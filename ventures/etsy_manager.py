"""
OpenClaw — Etsy Manager
Connects to Etsy API v3 to create listings after operator approval.
Listings are drafted (not published) until you approve in Discord.

Setup required:
1. Create Etsy developer account at developers.etsy.com
2. Create an app → get API key
3. Complete OAuth2 flow to get access token
4. Add ETSY_API_KEY + ETSY_ACCESS_TOKEN to Railway variables
"""

import json
import logging
import asyncio
import aiohttp
import discord
from datetime import datetime
from config.settings import settings

logger = logging.getLogger("openclaw.etsy")

ETSY_BASE = "https://openapi.etsy.com/v3"


class EtsyClient:
    """Async Etsy API v3 client."""

    def __init__(self):
        self.api_key      = settings.ETSY_API_KEY or ""
        self.access_token = settings.ETSY_ACCESS_TOKEN or ""
        self.shop_id      = settings.ETSY_SHOP_ID or ""

    def _headers(self) -> dict:
        return {
            "x-api-key":     self.api_key,
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type":  "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self.api_key and self.access_token and self.shop_id)

    async def get_shop(self) -> dict:
        """Verify shop connection."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ETSY_BASE}/application/shops/{self.shop_id}",
                headers=self._headers()
            ) as resp:
                return await resp.json()

    async def create_draft_listing(self, listing_data: dict) -> dict:
        """
        Creates a DRAFT listing on Etsy (not published, invisible to buyers).
        You review it in your Etsy dashboard before activating.
        """
        payload = {
            "quantity":          999,
            "title":             listing_data.get('title', '')[:140],
            "description":       listing_data.get('description', ''),
            "price":             float(listing_data.get('price', 9.00)),
            "who_made":          "i_did",
            "when_made":         "2020_2024",
            "taxonomy_id":       2078,     # Digital prints → digital downloads
            "type":              "download",
            "is_digital":        True,
            "should_auto_renew": True,
            "tags":              listing_data.get('tags', [])[:13],
            "materials":         ["digital download"],
            "shipping_profile_id": None,   # Not needed for digital
            "state":             "draft",  # DRAFT — safe, not visible to buyers
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ETSY_BASE}/application/shops/{self.shop_id}/listings",
                headers=self._headers(),
                json=payload
            ) as resp:
                result = await resp.json()
                if resp.status in (200, 201):
                    logger.info(f"Draft listing created: {result.get('listing_id')}")
                else:
                    logger.error(f"Etsy listing error {resp.status}: {result}")
                return {"status": resp.status, "data": result}

    async def activate_listing(self, listing_id: int) -> dict:
        """Activates a draft listing — makes it live on Etsy."""
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{ETSY_BASE}/application/shops/{self.shop_id}/listings/{listing_id}",
                headers=self._headers(),
                json={"state": "active"}
            ) as resp:
                result = await resp.json()
                return {"status": resp.status, "data": result}

    async def get_listings(self, state: str = "draft") -> list:
        """Get shop listings by state."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ETSY_BASE}/application/shops/{self.shop_id}/listings",
                headers=self._headers(),
                params={"state": state, "limit": 25}
            ) as resp:
                result = await resp.json()
                return result.get('results', [])


# ── Discord Views for Etsy Approval ──────────────────────────

class EtsyApprovalView(discord.ui.View):
    """
    Approve/Edit/Skip buttons for a pending Etsy listing.
    Approve → creates draft on Etsy (still invisible to buyers)
    Activate → makes it live immediately
    Skip → drops this listing
    """

    def __init__(self, listing_data: dict, product_data: dict, bot_ref):
        super().__init__(timeout=None)
        self.listing_data = listing_data
        self.product_data = product_data
        self.bot_ref      = bot_ref
        self.etsy         = EtsyClient()

    @discord.ui.button(label="📋 Create Draft on Etsy", style=discord.ButtonStyle.primary, emoji="📋")
    async def create_draft(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.etsy.is_configured():
            await interaction.response.send_message(
                "⚠️ Etsy not configured yet. Add `ETSY_API_KEY`, `ETSY_ACCESS_TOKEN`, "
                "and `ETSY_SHOP_ID` to Railway variables.\n"
                "See #commands → `/etsy setup` for instructions.",
                ephemeral=False
            )
            return

        await interaction.response.send_message("📋 Creating draft listing on Etsy...", ephemeral=False)

        result = await self.etsy.create_draft_listing(self.listing_data)

        if result['status'] in (200, 201):
            listing_id = result['data'].get('listing_id')
            listing_url = f"https://www.etsy.com/listing/{listing_id}"
            await interaction.followup.send(
                f"✅ **Draft created on Etsy!**\n"
                f"Listing ID: `{listing_id}`\n"
                f"**It's a draft — invisible to buyers until you activate it.**\n"
                f"Review it in your Etsy dashboard, then tap Activate when ready.\n"
                f"URL (active after activation): {listing_url}",
                ephemeral=False
            )
            # Store listing ID for activation
            self.listing_data['etsy_listing_id'] = listing_id
        else:
            error = result['data'].get('error', 'Unknown error')
            await interaction.followup.send(
                f"❌ Etsy error: {error}\n"
                f"Check your API credentials in Railway variables.",
                ephemeral=False
            )

    @discord.ui.button(label="🚀 Draft + Activate Now", style=discord.ButtonStyle.success, emoji="🚀")
    async def activate_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.etsy.is_configured():
            await interaction.response.send_message(
                "⚠️ Etsy not configured. Add API keys to Railway variables first.",
                ephemeral=False
            )
            return

        await interaction.response.send_message("🚀 Creating and activating listing on Etsy...", ephemeral=False)

        # Create draft first
        result = await self.etsy.create_draft_listing(self.listing_data)

        if result['status'] in (200, 201):
            listing_id = result['data'].get('listing_id')

            # Activate immediately
            await asyncio.sleep(1)
            activate_result = await self.etsy.activate_listing(listing_id)

            if activate_result['status'] in (200, 201):
                listing_url = f"https://www.etsy.com/listing/{listing_id}"
                await interaction.followup.send(
                    f"🎉 **Listing is LIVE on Etsy!**\n"
                    f"URL: {listing_url}\n"
                    f"Listing ID: `{listing_id}`\n"
                    f"Price: {self.listing_data.get('price', '$9')}\n"
                    f"*Share the URL on social media to drive first sales!*",
                    ephemeral=False
                )
                # Log to revenue channel
                if hasattr(self.bot_ref, 'active_ventures'):
                    for v in self.bot_ref.active_ventures:
                        if v.get('niche') == self.product_data.get('niche'):
                            v['etsy_listing_id'] = listing_id
                            v['etsy_url']         = listing_url
                            v['listed_at']        = datetime.now().isoformat()
            else:
                await interaction.followup.send(
                    f"⚠️ Draft created (ID: {listing_id}) but activation failed.\n"
                    f"Activate it manually in your Etsy dashboard.",
                    ephemeral=False
                )
        else:
            error = result['data'].get('error', 'Unknown error')
            await interaction.followup.send(f"❌ Etsy error: {error}", ephemeral=False)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏭️ Listing skipped.", ephemeral=False)
        self.stop()


def listing_approval_embed(listing_data: dict, product_data: dict) -> discord.Embed:
    """Rich embed showing the complete listing ready for Etsy approval."""

    def trunc(text, n=1024):
        if not text: return "N/A"
        return str(text)[:n-3] + "..." if len(str(text)) > n else str(text)

    ptype = product_data.get('type', 'product').upper()
    color = 0x00f5a0 if ptype == "PDF" else 0xb060ff

    embed = discord.Embed(
        title=trunc(f"🏪 Ready to List: {listing_data.get('title', 'Product')[:80]}", 256),
        description=(
            f"**Type:** {ptype} Digital Product\n"
            f"**Price:** {listing_data.get('price', '$9')}\n"
            f"Tap a button below to list on Etsy."
        ),
        color=color,
        timestamp=datetime.utcnow()
    )

    # Title preview
    embed.add_field(
        name="📝 Etsy Title",
        value=f"```{trunc(listing_data.get('title', ''), 950)}```",
        inline=False
    )

    # Tags
    tags = listing_data.get('tags', [])
    if tags:
        embed.add_field(
            name="🏷️ Tags (13)",
            value=trunc(", ".join(tags)),
            inline=False
        )

    # Product summary
    if product_data.get('summary'):
        embed.add_field(
            name="📦 Product Summary",
            value=trunc(product_data['summary'], 400),
            inline=False
        )

    embed.set_footer(text="OpenClaw Etsy Manager • Draft = safe preview, Activate = goes live")
    return embed


# ── Etsy Setup Guide ──────────────────────────────────────────

ETSY_SETUP_GUIDE = """**🏪 Etsy API Setup — 3 Steps**

**Step 1 — Create Etsy Shop**
Go to etsy.com/sell → set up your shop (free, takes 10 min)
Pick a shop name related to your niche (e.g. "ZenProductivity" or "FounderFiles")

**Step 2 — Get API Key**
1. Go to developers.etsy.com → Register as a developer
2. Create a new app → name it OpenClaw
3. Copy the **Keystring** → this is your `ETSY_API_KEY`

**Step 3 — Get Access Token + Shop ID**
1. In Railway → add `ETSY_API_KEY` first
2. Type `/etsy auth` in Discord — OpenClaw will give you an OAuth link
3. Click it → authorize OpenClaw → you'll get an access token
4. Add `ETSY_ACCESS_TOKEN` and `ETSY_SHOP_ID` to Railway

Once all 3 variables are set, listing buttons will go live.
Type `/etsy test` to verify the connection."""
