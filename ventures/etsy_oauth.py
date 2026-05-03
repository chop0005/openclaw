"""
OpenClaw — Etsy OAuth Manager
Handles the full Etsy OAuth2 PKCE flow.
/etsy auth → gives you a link → you authorize → token saved automatically.

How it works:
1. Bot generates OAuth URL with PKCE code verifier
2. You click the link and authorize your Etsy shop
3. Etsy redirects to our Railway callback URL
4. We exchange the code for an access token
5. Token is saved and bot confirms in Discord
"""

import aiohttp
import asyncio
import hashlib
import base64
import secrets
import logging
import json
import os
from datetime import datetime
from aiohttp import web
from config.settings import settings

logger = logging.getLogger("openclaw.etsy_oauth")

ETSY_BASE     = "https://openapi.etsy.com/v3"
ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"

# Scopes needed for OpenClaw
SCOPES = "listings_r listings_w listings_d shops_r transactions_r"

# Store pending OAuth state
_pending: dict = {}
_bot_ref = None
_channel_ref = None


def set_bot_ref(bot, channel):
    global _bot_ref, _channel_ref
    _bot_ref    = bot
    _channel_ref = channel


def generate_pkce_pair():
    """Generates PKCE code verifier and challenge."""
    verifier  = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b'=').decode()
    return verifier, challenge


def get_redirect_uri() -> str:
    """Returns the callback URL Railway will serve."""
    base = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if base:
        return f"https://{base}/etsy/callback"
    # Fallback for local dev
    port = settings.PORT
    return f"http://localhost:{port}/etsy/callback"


async def generate_auth_url() -> tuple[str, str]:
    """
    Generates the Etsy OAuth URL.
    Returns (auth_url, state) — state is used to verify the callback.
    """
    verifier, challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    # Store pending state
    _pending[state] = {"verifier": verifier, "created_at": datetime.now().isoformat()}

    params = {
        "response_type":         "code",
        "redirect_uri":          get_redirect_uri(),
        "scope":                 SCOPES,
        "client_id":             settings.ETSY_API_KEY or "",
        "state":                 state,
        "code_challenge":        challenge,
        "code_challenge_method": "S256",
    }

    query = "&".join([f"{k}={v}" for k, v in params.items()])
    auth_url = f"{ETSY_AUTH_URL}?{query}"

    return auth_url, state


async def exchange_code_for_token(code: str, state: str) -> dict:
    """
    Exchanges the authorization code for an access token.
    """
    if state not in _pending:
        return {"error": "Invalid or expired state. Try /etsy auth again."}

    verifier = _pending.pop(state)["verifier"]

    payload = {
        "grant_type":    "authorization_code",
        "client_id":     settings.ETSY_API_KEY or "",
        "redirect_uri":  get_redirect_uri(),
        "code":          code,
        "code_verifier": verifier,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            ETSY_TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                logger.info("Etsy OAuth token received successfully")
                return {"success": True, "data": data}
            else:
                logger.error(f"Token exchange failed {resp.status}: {data}")
                return {"success": False, "error": data.get("error_description", str(data))}


async def get_shop_id(access_token: str) -> str:
    """Gets the shop ID using the access token."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{ETSY_BASE}/application/users/me",
            headers={
                "x-api-key":     settings.ETSY_API_KEY or "",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return str(data.get("shop_id", ""))
            return ""


# ── OAuth Callback Web Handler ────────────────────────────────

async def handle_etsy_callback(request: web.Request) -> web.Response:
    """
    Handles the Etsy OAuth callback.
    Etsy redirects here after the user authorizes.
    """
    code  = request.rel_url.query.get("code", "")
    state = request.rel_url.query.get("state", "")
    error = request.rel_url.query.get("error", "")

    if error:
        logger.error(f"Etsy OAuth error: {error}")
        if _channel_ref:
            await _channel_ref.send(
                f"❌ Etsy authorization failed: {error}\n"
                f"Try `/etsy auth` again."
            )
        return web.Response(
            text="❌ Authorization failed. Go back to Discord and try /etsy auth again.",
            content_type="text/plain"
        )

    if not code or not state:
        return web.Response(
            text="❌ Missing code or state. Try /etsy auth again.",
            content_type="text/plain"
        )

    # Exchange code for token
    result = await exchange_code_for_token(code, state)

    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        if _channel_ref:
            await _channel_ref.send(f"❌ Token exchange failed: {error_msg}")
        return web.Response(
            text=f"❌ Failed to get access token: {error_msg}",
            content_type="text/plain"
        )

    token_data    = result["data"]
    access_token  = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")

    # Get shop ID
    shop_id = await get_shop_id(access_token)

    # Save tokens to environment (in-memory for now)
    # In production you'd save these to a database
    os.environ["ETSY_ACCESS_TOKEN"]  = access_token
    os.environ["ETSY_SHOP_ID"]       = shop_id
    if refresh_token:
        os.environ["ETSY_REFRESH_TOKEN"] = refresh_token

    # Update settings object
    settings.ETSY_ACCESS_TOKEN = access_token
    settings.ETSY_SHOP_ID      = shop_id

    logger.info(f"Etsy OAuth complete. Shop ID: {shop_id}")

    # Notify in Discord
    if _channel_ref:
        await _channel_ref.send(
            f"🎉 **Etsy connected successfully!**\n\n"
            f"**Access Token:** `{access_token[:20]}...` (saved)\n"
            f"**Shop ID:** `{shop_id}`\n\n"
            f"⚠️ **Important:** Add these to Railway variables permanently:\n"
            f"`ETSY_ACCESS_TOKEN` = `{access_token}`\n"
            f"`ETSY_SHOP_ID` = `{shop_id}`\n\n"
            f"Railway variables persist between restarts — in-memory tokens are lost on redeploy."
        )

    return web.Response(
        text=(
            "✅ Etsy connected! Go back to Discord.\n\n"
            f"Shop ID: {shop_id}\n\n"
            "IMPORTANT: Copy your ETSY_ACCESS_TOKEN and ETSY_SHOP_ID "
            "from Discord and add them to Railway variables."
        ),
        content_type="text/plain"
    )


async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint — Railway uses this to verify the service is up."""
    return web.Response(
        text=json.dumps({
            "status":    "online",
            "service":   "OpenClaw",
            "timestamp": datetime.now().isoformat()
        }),
        content_type="application/json"
    )


async def start_web_server(port: int = 8080):
    """
    Starts a lightweight web server alongside the Discord bot.
    Handles Etsy OAuth callback and health checks.
    """
    app = web.Application()
    app.router.add_get("/",                handle_health)
    app.router.add_get("/health",          handle_health)
    app.router.add_get("/etsy/callback",   handle_etsy_callback)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"✅ Web server running on port {port}")
    logger.info(f"   Health: http://localhost:{port}/health")
    logger.info(f"   Etsy callback: http://localhost:{port}/etsy/callback")

    return runner
