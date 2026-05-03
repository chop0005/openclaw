"""
OpenClaw — Auto Social Poster
Posts to TikTok, Instagram, X/Twitter, Pinterest, Reddit automatically.
Runs on a schedule, repurposes content across all platforms.
Tracks which posts drive the most traffic.

Platform integrations:
- TikTok:    TikTok for Business API (video captions + auto-schedule)
- Instagram: Instagram Graph API via Meta Business
- X/Twitter: Twitter API v2
- Pinterest: Pinterest API v5 (already built)
- Reddit:    Reddit API (PRAW)

For platforms without API keys configured, generates content
and posts it to #social-posts for manual posting.
"""

import asyncio
import json
import logging
import discord
from datetime import datetime, timedelta
from utils.claude import think_json, think
from config.settings import settings

logger = logging.getLogger("openclaw.social_poster")

SYSTEM = """You are OpenClaw's Social Media Content Engine.
You create viral, platform-native content that drives clicks to digital product stores.
Each platform needs completely different content — what works on Reddit fails on TikTok.
Always respond with valid JSON only."""

# Optimal posting times (EST)
POSTING_SCHEDULE = {
    "tiktok":    ["7:00 AM", "12:00 PM", "7:00 PM", "9:00 PM"],
    "instagram": ["6:00 AM", "11:00 AM", "7:00 PM"],
    "twitter":   ["8:00 AM", "12:00 PM", "5:00 PM", "9:00 PM"],
    "pinterest": ["8:00 PM", "9:00 PM", "10:00 PM"],
    "reddit":    ["9:00 AM", "12:00 PM", "5:00 PM"],
}

PLATFORM_COLORS = {
    "tiktok":    0x000000,
    "instagram": 0xe1306c,
    "twitter":   0x1da1f2,
    "pinterest": 0xe60023,
    "reddit":    0xff4500,
}

PLATFORM_EMOJIS = {
    "tiktok":    "🎬",
    "instagram": "📸",
    "twitter":   "🐦",
    "pinterest": "📌",
    "reddit":    "🔴",
}


async def generate_platform_content(
    product_name: str,
    niche: str,
    product_url: str,
    price: str,
    platform: str
) -> dict:
    """Generates platform-native content for a specific platform."""

    platform_guides = {
        "tiktok": """TikTok: Hook in first 2 seconds. Use trending sounds reference.
                    POV/story format. 150-300 chars. 3-5 hashtags. Drive to bio link.""",
        "instagram": """Instagram: Aesthetic description. Line breaks for readability.
                       Mix of niche hashtags (30). CTA to link in bio. 150-300 chars.""",
        "twitter": """X/Twitter: Punchy, opinionated. Under 280 chars.
                     Problem → solution format. 1-2 hashtags max. Direct link.""",
        "pinterest": """Pinterest: Keyword-rich title and description.
                       Aspirational language. 'How to' or 'ideas' framing.
                       100-300 chars. No hashtags needed.""",
        "reddit": """Reddit: Authentic, non-salesy. Community-first tone.
                   Share the story/journey, product is secondary.
                   Fits naturally into relevant subreddit. No hard selling.""",
    }

    prompt = f"""Create a {platform} post for this digital product:

Product: {product_name}
Niche: {niche}
Price: {price}
Link: {product_url or 'link in bio'}

Platform guide: {platform_guides.get(platform, '')}

Return JSON:
{{
  "platform": "{platform}",
  "content": "The actual post text ready to copy-paste",
  "hashtags": ["tag1", "tag2", "tag3"],
  "hook": "Opening line that stops the scroll",
  "cta": "Call to action",
  "best_time": "Best time to post",
  "subreddit": "Best subreddit to post in (Reddit only)",
  "image_description": "Description of ideal image/thumbnail to pair with this",
  "expected_reach": "Estimated organic reach for new account",
  "viral_angle": "What makes this shareable"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=1000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {
            "platform": platform,
            "content": f"Just launched: {product_name} — {price} digital download. Link in bio! #{niche.replace(' ','').lower()}",
            "hashtags": [niche.replace(' ','').lower(), "digitalproducts", "etsy"],
            "hook": f"This {price} template is changing how people handle {niche}",
            "cta": "Link in bio",
            "best_time": POSTING_SCHEDULE.get(platform, ["12:00 PM"])[0],
            "image_description": f"Clean mockup of {product_name}",
            "expected_reach": "100-500 for new account",
            "viral_angle": "Problem-solution format"
        }


async def generate_content_batch(
    product_name: str,
    niche: str,
    product_url: str = "",
    price: str = "$9",
    platforms: list = None
) -> list:
    """Generates content for all platforms at once."""
    if platforms is None:
        platforms = ["tiktok", "instagram", "twitter", "pinterest", "reddit"]

    results = []
    for platform in platforms:
        content = await generate_platform_content(
            product_name, niche, product_url, price, platform
        )
        results.append(content)
        await asyncio.sleep(0.5)  # slight delay between API calls

    return results


# ── Platform API Posters ──────────────────────────────────────

async def post_to_twitter(content: dict) -> dict:
    """Posts to X/Twitter via API v2."""
    if not settings.TWITTER_BEARER_TOKEN:
        return {"success": False, "error": "No Twitter API key", "manual": True}

    import aiohttp
    text = content.get("content", "")
    hashtags = content.get("hashtags", [])
    if hashtags:
        text += " " + " ".join([f"#{h}" for h in hashtags[:2]])

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.twitter.com/2/tweets",
                json={"text": text[:280]},
                headers={
                    "Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                if resp.status in (200, 201):
                    tweet_id = data.get("data", {}).get("id", "")
                    return {
                        "success": True,
                        "url": f"https://twitter.com/i/web/status/{tweet_id}",
                        "platform": "twitter"
                    }
                return {"success": False, "error": str(data), "manual": True}
    except Exception as e:
        return {"success": False, "error": str(e), "manual": True}


async def post_to_reddit(content: dict, product_name: str) -> dict:
    """Posts to Reddit via API."""
    if not (settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET):
        return {"success": False, "error": "No Reddit API keys", "manual": True}

    import aiohttp

    subreddit = content.get("subreddit", "SideProject")
    post_text = content.get("content", "")

    try:
        # Get access token
        async with aiohttp.ClientSession() as session:
            auth = aiohttp.BasicAuth(
                settings.REDDIT_CLIENT_ID,
                settings.REDDIT_CLIENT_SECRET
            )
            async with session.post(
                "https://www.reddit.com/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=auth,
                headers={"User-Agent": "OpenClaw/1.0"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                token_data = await resp.json()
                access_token = token_data.get("access_token", "")

            if not access_token:
                return {"success": False, "error": "Reddit auth failed", "manual": True}

            # Submit post
            async with session.post(
                "https://oauth.reddit.com/api/submit",
                data={
                    "sr":    subreddit,
                    "kind":  "self",
                    "title": product_name,
                    "text":  post_text,
                    "resubmit": True,
                },
                headers={
                    "Authorization": f"bearer {access_token}",
                    "User-Agent":    "OpenClaw/1.0"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                url = data.get("jquery", [[]])[10][3][0] if data.get("jquery") else ""
                return {
                    "success": True,
                    "url":     url,
                    "platform": "reddit",
                    "subreddit": subreddit
                }
    except Exception as e:
        return {"success": False, "error": str(e), "manual": True}


async def post_to_platform(platform: str, content: dict, product_name: str) -> dict:
    """Routes to the right platform poster."""
    if platform == "twitter":
        return await post_to_twitter(content)
    elif platform == "reddit":
        return await post_to_reddit(content, product_name)
    else:
        # Pinterest is handled by pinterest_manager
        # TikTok and Instagram require manual posting (API restrictions)
        return {"success": False, "error": f"{platform} requires manual posting", "manual": True}


# ── Discord Embeds ────────────────────────────────────────────

def content_card_embed(content: dict, product_name: str, auto_posted: bool = False) -> discord.Embed:
    """Rich embed for a content piece."""
    platform = content.get("platform", "social")
    color    = PLATFORM_COLORS.get(platform, 0x00c8f0)
    emoji    = PLATFORM_EMOJIS.get(platform, "📱")

    status = "✅ AUTO-POSTED" if auto_posted else "📋 READY TO POST"

    embed = discord.Embed(
        title=f"{emoji} {platform.upper()} — {status}",
        color=color,
        timestamp=datetime.utcnow()
    )

    post_text = content.get("content", "")
    if post_text:
        embed.add_field(
            name="📝 Post (copy-paste ready)",
            value=f"```{post_text[:900]}```",
            inline=False
        )

    if content.get("hook"):
        embed.add_field(name="🪝 Hook", value=content["hook"][:200], inline=True)
    if content.get("best_time"):
        embed.add_field(name="⏰ Best Time", value=content["best_time"], inline=True)
    if content.get("expected_reach"):
        embed.add_field(name="📊 Est. Reach", value=content["expected_reach"], inline=True)

    hashtags = content.get("hashtags", [])
    if hashtags and platform in ("instagram", "tiktok"):
        embed.add_field(
            name="🏷️ Hashtags",
            value=" ".join([f"#{h}" for h in hashtags[:10]]),
            inline=False
        )

    if content.get("subreddit") and platform == "reddit":
        embed.add_field(name="📍 Subreddit", value=f"r/{content['subreddit']}", inline=True)

    if content.get("image_description"):
        embed.add_field(
            name="🖼️ Image/Thumbnail",
            value=content["image_description"][:200],
            inline=False
        )

    if auto_posted and content.get("post_url"):
        embed.add_field(name="🔗 Live Post", value=content["post_url"], inline=False)

    embed.set_footer(text=f"OpenClaw Auto-Poster • {product_name}")
    return embed


class PostApprovalView(discord.ui.View):
    """Post now / Schedule / Skip buttons."""

    def __init__(self, content: dict, product_name: str, bot_ref):
        super().__init__(timeout=None)
        self.content      = content
        self.product_name = product_name
        self.bot_ref      = bot_ref

    @discord.ui.button(label="🚀 Post Now", style=discord.ButtonStyle.success)
    async def post_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        platform = self.content.get("platform", "")
        await interaction.response.send_message(
            f"🚀 Posting to {platform.upper()}...", ephemeral=False
        )
        result = await post_to_platform(platform, self.content, self.product_name)

        if result.get("success"):
            url = result.get("url", "")
            await interaction.followup.send(
                f"✅ Posted to {platform.upper()}!"
                + (f"\n🔗 {url}" if url else ""),
                ephemeral=False
            )
        elif result.get("manual"):
            await interaction.followup.send(
                f"📋 **{platform.upper()} requires manual posting.**\n"
                f"Copy the text above and paste it into {platform}.",
                ephemeral=False
            )
        else:
            await interaction.followup.send(
                f"❌ Failed: {result.get('error', 'Unknown error')}",
                ephemeral=False
            )
        self.stop()

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏭️ Skipped.", ephemeral=False)
        self.stop()


# ── Main Scheduler ────────────────────────────────────────────

async def run_social_poster(bot, channel_id: int):
    """
    Auto-generates and posts content for all active ventures.
    Runs every 8 hours. Auto-posts where API allows, manual otherwise.
    """
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        logger.error(f"Social posts channel {channel_id} not found")
        return

    logger.info("Social Poster running")
    posted_for = set()

    while not bot.is_closed():
        try:
            ventures = getattr(bot, 'active_ventures', [])

            for venture in ventures:
                niche    = venture.get('niche', '')
                research = venture.get('research', {})
                listing  = venture.get('listing', {})

                if not niche:
                    continue

                product_name = research.get('product_name', niche)
                price        = research.get('price_point', '$9')
                etsy_url     = venture.get('etsy_url', '')
                gumroad_url  = venture.get('gumroad_url', '')
                product_url  = etsy_url or gumroad_url or ''

                # Generate fresh content batch every 8 hours
                batch_key = f"{niche}_{datetime.now().strftime('%Y%m%d%H')}"
                if batch_key in posted_for:
                    continue
                posted_for.add(batch_key)

                await channel.send(embed=discord.Embed(
                    description=f"📱 Generating social content for **{product_name}**...",
                    color=0x1e3d52, timestamp=datetime.utcnow()
                ))

                contents = await generate_content_batch(
                    product_name, niche, product_url, price
                )

                auto_posted = 0
                for content in contents:
                    platform = content.get("platform", "")

                    # Try to auto-post where API is available
                    result = await post_to_platform(platform, content, product_name)
                    auto = result.get("success", False)
                    if auto:
                        auto_posted += 1
                        content["post_url"] = result.get("url", "")

                    embed = content_card_embed(content, product_name, auto_posted=auto)
                    view  = PostApprovalView(content, product_name, bot) if not auto else None

                    if view:
                        await channel.send(embed=embed, view=view)
                    else:
                        await channel.send(embed=embed)
                    await asyncio.sleep(1)

                await channel.send(
                    f"✅ Content batch complete for **{product_name}**\n"
                    f"Auto-posted: {auto_posted}/5 | Manual needed: {5-auto_posted}/5"
                )

        except Exception as e:
            logger.error(f"Social poster error: {e}")

        # Run every 8 hours
        await asyncio.sleep(8 * 60 * 60)
