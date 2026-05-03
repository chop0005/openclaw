"""
OpenClaw — Competitor Scanner
Monitors top sellers in your niche.
Finds gaps, spots new products, tracks pricing changes.
Posts weekly intelligence reports.
"""

import asyncio
import json
import logging
import discord
from datetime import datetime
from utils.claude import think_json
from config.settings import settings

logger = logging.getLogger("openclaw.competitor_scanner")

SYSTEM = """You are OpenClaw's Competitive Intelligence Analyst.
You analyze competitor strategies and find exploitable gaps.
You give specific, actionable intelligence — not generic advice.
Always respond with valid JSON only."""


async def scan_competitors(niche: str) -> dict:
    """Scans the competitive landscape for a niche."""
    prompt = f"""Analyze the competitive landscape on Etsy for: {niche}

Based on what you know about Etsy marketplace dynamics as of {datetime.now().strftime('%B %Y')}:

Return JSON:
{{
  "niche": "{niche}",
  "market_overview": "Current state of this niche on Etsy",
  "top_seller_patterns": [
    {{
      "pattern": "What top sellers do",
      "example": "Specific example",
      "why_it_works": "The psychology/mechanics behind it"
    }}
  ],
  "pricing_landscape": {{
    "low_end": "$X",
    "mid_range": "$Y",
    "premium": "$Z",
    "sweet_spot": "Where most sales happen",
    "opportunity": "Where you can position profitably"
  }},
  "content_gaps": [
    "Specific product type that's underserved",
    "Specific keyword with low competition",
    "Specific audience segment being ignored"
  ],
  "trending_formats": ["Format 1 that's gaining traction", "Format 2"],
  "competitor_weaknesses": ["Common weakness 1", "Common weakness 2"],
  "winning_keywords": ["keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5"],
  "recommended_differentiation": "How to stand out specifically",
  "new_product_ideas": [
    {{"name": "Product idea", "gap_it_fills": "What's missing in market"}}
  ],
  "threat_level": "low | medium | high",
  "opportunity_score": 80
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=2500)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {}


def competitor_embed(data: dict, niche: str) -> discord.Embed:
    """Rich embed for competitor intelligence report."""
    score = data.get("opportunity_score", 0)
    threat = data.get("threat_level", "medium")

    threat_colors = {"low": 0x00f5a0, "medium": 0xffc944, "high": 0xff7733}
    color = threat_colors.get(threat, 0x00c8f0)

    embed = discord.Embed(
        title=f"🕵️ Competitor Intel: {niche[:60]}",
        description=data.get("market_overview", "")[:400],
        color=color,
        timestamp=datetime.utcnow()
    )

    pricing = data.get("pricing_landscape", {})
    if pricing:
        embed.add_field(
            name="💰 Pricing Landscape",
            value=(
                f"Low: {pricing.get('low_end','?')} | "
                f"Mid: {pricing.get('mid_range','?')} | "
                f"Premium: {pricing.get('premium','?')}\n"
                f"**Sweet spot:** {pricing.get('sweet_spot','?')}\n"
                f"**Your opportunity:** {pricing.get('opportunity','?')}"
            ),
            inline=False
        )

    gaps = data.get("content_gaps", [])
    if gaps:
        embed.add_field(
            name="🕳️ Market Gaps to Exploit",
            value="\n".join([f"• {g}" for g in gaps[:4]]),
            inline=False
        )

    weaknesses = data.get("competitor_weaknesses", [])
    if weaknesses:
        embed.add_field(
            name="⚡ Competitor Weaknesses",
            value="\n".join([f"• {w}" for w in weaknesses[:3]]),
            inline=True
        )

    keywords = data.get("winning_keywords", [])
    if keywords:
        embed.add_field(
            name="🔍 Keywords to Target",
            value=" • ".join(keywords[:5]),
            inline=False
        )

    new_products = data.get("new_product_ideas", [])
    if new_products:
        prod_text = "\n".join([
            f"• **{p.get('name')}** — {p.get('gap_it_fills','')[:80]}"
            for p in new_products[:3]
        ])
        embed.add_field(name="💡 New Product Ideas", value=prod_text, inline=False)

    if data.get("recommended_differentiation"):
        embed.add_field(
            name="🎯 How to Differentiate",
            value=data["recommended_differentiation"][:512],
            inline=False
        )

    embed.add_field(
        name="📊 Metrics",
        value=f"Opportunity: **{score}/100** | Threat: **{threat.upper()}**",
        inline=False
    )

    embed.set_footer(text="OpenClaw Competitor Scanner • Updated weekly")
    return embed


async def run_competitor_scanner(bot, channel_id: int):
    """Weekly competitor intelligence for all active ventures."""
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    logger.info("Competitor Scanner running (weekly)")

    while not bot.is_closed():
        try:
            ventures = getattr(bot, 'active_ventures', [])

            if ventures:
                await channel.send(embed=discord.Embed(
                    description="🕵️ Running weekly competitor intelligence scan...",
                    color=0x1e3d52, timestamp=datetime.utcnow()
                ))

                for venture in ventures[:3]:
                    niche = venture.get('niche', '')
                    if not niche:
                        continue
                    data = await scan_competitors(niche)
                    if data:
                        await channel.send(embed=competitor_embed(data, niche))
                    await asyncio.sleep(3)
            else:
                # No ventures yet - scan top niches
                default_niches = ["Notion templates", "digital planners", "Canva templates"]
                for niche in default_niches:
                    data = await scan_competitors(niche)
                    if data:
                        await channel.send(embed=competitor_embed(data, niche))
                    await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"Competitor scanner error: {e}")

        await asyncio.sleep(7 * 24 * 60 * 60)
