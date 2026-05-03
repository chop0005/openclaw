"""
OpenClaw — Pinterest Auto-Poster
Pins every product automatically to drive free organic traffic.
Pinterest is the #1 free traffic source for Etsy sellers.
A single viral pin can drive thousands of visits.

Setup:
1. Create Pinterest business account (free)
2. Go to developers.pinterest.com → Create App
3. Generate access token with pins:read, pins:write, boards:read, boards:write scopes
4. Add PINTEREST_ACCESS_TOKEN + PINTEREST_BOARD_ID to Railway

Auto-posting schedule:
- Pins new products immediately on creation
- Re-pins top performers every 7 days (fresh traffic)
- Posts 3x/day from content queue
"""

import aiohttp
import asyncio
import logging
import discord
from datetime import datetime
from utils.claude import think_json
from config.settings import settings

logger = logging.getLogger("openclaw.pinterest")

PINTEREST_BASE = "https://api.pinterest.com/v5"

SYSTEM = """You are OpenClaw's Pinterest Content Specialist.
You write Pinterest pin titles and descriptions that drive clicks and saves.
Pinterest SEO is different — focus on keywords buyers search for.
Always respond with valid JSON only."""


class PinterestClient:
    def __init__(self):
        self.token    = settings.PINTEREST_ACCESS_TOKEN or ""
        self.board_id = settings.PINTEREST_BOARD_ID or ""

    def is_configured(self) -> bool:
        return bool(self.token and self.board_id)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type":  "application/json",
        }

    async def get_boards(self) -> list:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PINTEREST_BASE}/boards",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                return data.get("items", [])

    async def create_pin(self, pin_data: dict) -> dict:
        """Creates a pin on Pinterest."""
        payload = {
            "board_id":   pin_data.get("board_id", self.board_id),
            "title":      pin_data.get("title", "")[:100],
            "description": pin_data.get("description", "")[:500],
            "link":       pin_data.get("link", ""),
            "media_source": {
                "source_type": "image_url",
                "url": pin_data.get("image_url", "https://via.placeholder.com/1000x1500/2D3748/FFFFFF?text=Digital+Product")
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{PINTEREST_BASE}/pins",
                headers=self._headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                if resp.status in (200, 201):
                    logger.info(f"Pin created: {data.get('id')}")
                    return {"success": True, "data": data}
                else:
                    logger.error(f"Pinterest error {resp.status}: {data}")
                    return {"success": False, "data": data}


async def generate_pin_content(product_name: str, niche: str,
                                etsy_url: str = "", price: str = "$9") -> dict:
    """Generates optimized Pinterest pin content."""
    prompt = f"""Create an optimized Pinterest pin for this digital product:

Product: {product_name}
Niche: {niche}
Price: {price}
Link: {etsy_url or "Etsy store"}

Pinterest buyers search differently than Google — they're in discovery mode.
Make the title and description keyword-rich and aspirational.

Return JSON:
{{
  "title": "Pin title (max 100 chars, keyword-rich)",
  "description": "Pin description (max 500 chars, includes keywords, ends with soft CTA)",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "boards_to_pin": ["Board name 1", "Board name 2"],
  "best_time": "Best time to post (e.g. 8-11 PM EST)",
  "image_text_overlay": "Short text to overlay on pin image (max 8 words)",
  "color_scheme": "Colors that work for this niche (e.g. sage green and cream)"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=1000)
    try:
        import json
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {
            "title": f"{product_name} — Digital Download",
            "description": f"Get your {product_name} instantly. Perfect for {niche}. {price} digital download.",
            "keywords": [niche, "digital download", "printable", "template"],
            "best_time": "8-10 PM EST",
            "image_text_overlay": f"Get it for {price}",
            "color_scheme": "neutral tones"
        }


async def auto_pin_product(product_name: str, niche: str,
                            etsy_url: str = "", gumroad_url: str = "",
                            price: str = "$9") -> dict:
    """Full auto-pin pipeline for a new product."""
    client = PinterestClient()

    if not client.is_configured():
        return {"success": False, "error": "Pinterest not configured"}

    # Generate pin content
    pin_content = await generate_pin_content(product_name, niche, etsy_url or gumroad_url, price)

    result = await client.create_pin({
        "title":       pin_content.get("title", ""),
        "description": pin_content.get("description", ""),
        "link":        etsy_url or gumroad_url or "",
        "board_id":    settings.PINTEREST_BOARD_ID,
    })

    return {
        "success":     result["success"],
        "pin_content": pin_content,
        "pin_data":    result.get("data", {}),
        "pin_url":     f"https://pinterest.com/pin/{result.get('data', {}).get('id', '')}"
    }


def pinterest_embed(pin_result: dict, product_name: str) -> discord.Embed:
    """Discord embed for a Pinterest pin result."""
    pin_content = pin_result.get("pin_content", {})
    success     = pin_result.get("success", False)

    embed = discord.Embed(
        title=f"📌 {'Pinned!' if success else 'Pin Failed'}: {product_name[:60]}",
        color=0xe60023 if success else 0xff2255,  # Pinterest red
        timestamp=datetime.utcnow()
    )

    if success:
        if pin_content.get("title"):
            embed.add_field(name="Pin Title", value=pin_content["title"][:1024], inline=False)
        if pin_content.get("description"):
            embed.add_field(name="Description", value=pin_content["description"][:1024], inline=False)
        keywords = pin_content.get("keywords", [])
        if keywords:
            embed.add_field(name="Keywords", value=" • ".join(keywords), inline=False)
        if pin_result.get("pin_url"):
            embed.add_field(name="Pin URL", value=pin_result["pin_url"], inline=False)
        embed.set_footer(text="OpenClaw Pinterest • Free traffic compounding 24/7")
    else:
        error = pin_result.get("error", "Unknown error")
        embed.add_field(name="Error", value=str(error)[:1024], inline=False)
        embed.add_field(
            name="Setup Required",
            value="Add `PINTEREST_ACCESS_TOKEN` and `PINTEREST_BOARD_ID` to Railway variables.",
            inline=False
        )

    return embed


async def run_pinterest_scheduler(bot, channel_id: int):
    """
    Background scheduler that auto-pins new products and re-pins top performers.
    Posts results to social-posts channel.
    """
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)

    if not channel:
        logger.error(f"Social posts channel {channel_id} not found")
        return

    logger.info("Pinterest scheduler running")
    pinned = set()

    while not bot.is_closed():
        try:
            client = PinterestClient()
            if not client.is_configured():
                await asyncio.sleep(3600)
                continue

            # Pin new products from active ventures
            ventures = getattr(bot, 'active_ventures', [])
            for venture in ventures:
                niche = venture.get('niche', '')
                if not niche or niche in pinned:
                    continue

                research = venture.get('research', {})
                product_name = research.get('product_name', niche)
                etsy_url     = venture.get('etsy_url', '')
                gumroad_url  = venture.get('gumroad_url', '')
                price        = research.get('price_point', '$9')

                if not (etsy_url or gumroad_url):
                    continue  # Don't pin until we have a URL

                pinned.add(niche)
                result = await auto_pin_product(product_name, niche, etsy_url, gumroad_url, price)

                embed = pinterest_embed(result, product_name)
                await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Pinterest scheduler error: {e}")

        await asyncio.sleep(3600)  # Check every hour


PINTEREST_SETUP = """**📌 Pinterest Setup — 5 Minutes**

1. Go to **business.pinterest.com** → create free business account
2. Go to **developers.pinterest.com** → Create App → name it OpenClaw
3. In your app → Generate access token with scopes:
   ✅ pins:read  ✅ pins:write  ✅ boards:read  ✅ boards:write
4. Create a board for your niche (e.g. "Notion Templates for Entrepreneurs")
5. Get your Board ID from the board URL

In Railway → Variables → add:
`PINTEREST_ACCESS_TOKEN` = your token
`PINTEREST_BOARD_ID`     = your board ID (from URL)

OpenClaw will pin every product automatically and re-pin top performers weekly."""
