"""
OpenClaw — Opportunity Scanner
Scans trends specifically for digital product opportunities.
Filters by: profit speed, low competition, automation potential.
Posts scored opportunities to #opportunities with approve buttons.
"""

import asyncio
import json
import logging
import discord
from datetime import datetime
from utils.claude import think_json
from ventures.base import rank_by_capital_and_speed, VENTURE_TYPES
from config.settings import settings

logger = logging.getLogger("openclaw.opportunity_scanner")

SYSTEM = """You are OpenClaw's Opportunity Scanner — an expert at finding
underserved digital product niches on Etsy and Gumroad.

You look for niches where:
- Search volume is high (people are actively buying)
- Competition is low-medium (not dominated by big sellers)
- The product can be made once and sold forever
- The buyer has a clear, urgent pain point
- $7-15 price point feels like a no-brainer

You base analysis on real Etsy search patterns, Reddit discussions,
Pinterest trends, and TikTok search data.

Always respond with valid JSON only."""


async def scan_for_opportunities(budget: float = 50.0) -> list[dict]:
    """
    Scans for the best digital product opportunities right now.
    Returns ranked list with venture type recommendations.
    """
    logger.info("Scanning for opportunities...")

    # Get best venture types for this budget
    ranked_types = rank_by_capital_and_speed(budget, settings.TARGET_DAYS)
    top_types = [v.key for v in ranked_types[:3]]

    prompt = f"""It's {datetime.now().strftime('%B %Y')}. Find 3 HIGH-POTENTIAL digital product opportunities.

Budget available: ${budget}
Target: ${settings.REVENUE_TARGET} in {settings.TARGET_DAYS} days
Best venture types for this budget: {', '.join(top_types)}

Look for niches that are:
1. Actively searched on Etsy RIGHT NOW
2. Have passionate buyers who spend money
3. Low-medium competition (under 5,000 competing listings ideally)
4. Products that take 2-4 hours to make
5. Buyers who leave reviews (social proof builds fast)

Strong niche examples (DON'T use these, find NEW ones):
- ADHD productivity planners
- Side hustle income tracker
- Freelancer client onboarding kit

Return a JSON array with 3 objects:
{{
  "niche": "Specific niche name",
  "venture_type": "digital_product | ai_tool | chrome_extension",
  "why_now": "Why this is hot RIGHT NOW (specific reason)",
  "buyer_pain": "The exact problem buyers have",
  "product_idea": "The specific first product to make",
  "etsy_search_term": "Exact search term buyers use on Etsy",
  "competition_level": "Low | Medium | High",
  "estimated_searches": "Approximate monthly Etsy searches",
  "price_range": "$7-9 | $9-15 | $15-25",
  "build_time": "Time to create the first product",
  "days_to_first_sale": 10,
  "monthly_potential": "$X-Y at 2-5 sales/day",
  "confidence_score": 85,
  "venture_fit_reason": "Why this venture type fits"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=2500)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        opps = json.loads(clean)
        opps.sort(key=lambda x: x.get('confidence_score', 0), reverse=True)
        logger.info(f"Found {len(opps)} opportunities")
        return opps if isinstance(opps, list) else []
    except Exception as e:
        logger.error(f"Opportunity scan error: {e}")
        return []


def opportunity_embed(opp: dict, rank: int) -> discord.Embed:
    """Rich Discord embed for an opportunity."""
    score = opp.get('confidence_score', 0)
    competition = opp.get('competition_level', 'Unknown')

    color_map = {
        "Low": 0x00f5a0,
        "Medium": 0xffc944,
        "High": 0xff7733
    }
    color = color_map.get(competition, 0x00c8f0)

    rank_emoji = ["🥇", "🥈", "🥉"][rank] if rank < 3 else "🔍"

    embed = discord.Embed(
        title=f"{rank_emoji} {opp.get('niche', 'Unknown Niche')}",
        description=f"*{opp.get('why_now', '')}*",
        color=color,
        timestamp=datetime.utcnow()
    )

    embed.add_field(name="💰 First Product", value=opp.get('product_idea', 'N/A'), inline=False)
    embed.add_field(name="😤 Buyer Pain", value=opp.get('buyer_pain', 'N/A'), inline=False)
    embed.add_field(name="🔍 Etsy Search Term", value=f"`{opp.get('etsy_search_term', 'N/A')}`", inline=True)
    embed.add_field(name="⚔️ Competition", value=competition, inline=True)
    embed.add_field(name="⏱️ Days to First Sale", value=str(opp.get('days_to_first_sale', '?')), inline=True)
    embed.add_field(name="💵 Price Range", value=opp.get('price_range', 'N/A'), inline=True)
    embed.add_field(name="🏗️ Build Time", value=opp.get('build_time', 'N/A'), inline=True)
    embed.add_field(name="📈 Monthly Potential", value=opp.get('monthly_potential', 'N/A'), inline=True)
    embed.add_field(name="🎯 Confidence", value=f"**{score}/100**", inline=True)
    embed.add_field(name="🔧 Venture Type", value=opp.get('venture_type', 'digital_product').replace('_', ' ').title(), inline=True)

    embed.set_footer(text=f"OpenClaw Opportunity Scanner • Target: ${settings.REVENUE_TARGET} in {settings.TARGET_DAYS} days")
    return embed


class OpportunityApproveView(discord.ui.View):
    """Approve button — triggers the full build pipeline for this opportunity."""

    def __init__(self, opportunity: dict, bot_ref):
        super().__init__(timeout=None)
        self.opportunity = opportunity
        self.bot_ref = bot_ref

    @discord.ui.button(label="✅ BUILD THIS", style=discord.ButtonStyle.success, emoji="🚀")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        niche = self.opportunity.get('niche', 'Unknown')
        await interaction.response.send_message(
            f"🚀 **{niche}** approved! OpenClaw is starting the build pipeline.\n"
            f"Watch **#build-pipeline** for live progress.",
            ephemeral=False
        )
        if not hasattr(self.bot_ref, 'approved_opportunities'):
            self.bot_ref.approved_opportunities = []
        self.bot_ref.approved_opportunities.append(self.opportunity)
        logger.info(f"Opportunity approved: {niche}")
        self.stop()

    @discord.ui.button(label="🔄 Rescan", style=discord.ButtonStyle.secondary)
    async def rescan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔄 Rescanning for alternatives...", ephemeral=False
        )

    @discord.ui.button(label="❌ Skip", style=discord.ButtonStyle.danger)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"⏭️ Skipped. OpenClaw will find alternatives next scan.", ephemeral=False
        )
        self.stop()


async def run_opportunity_scanner(bot, channel_id: int, interval_minutes: int = 240):
    """Main opportunity scanner loop — runs every 4 hours."""
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        logger.error(f"Opportunities channel {channel_id} not found")
        return

    logger.info(f"Opportunity Scanner running every {interval_minutes}m")

    while not bot.is_closed():
        try:
            await channel.send(
                embed=discord.Embed(
                    description=f"🔍 Scanning for opportunities... target: **${settings.REVENUE_TARGET} in {settings.TARGET_DAYS} days** | budget: **${settings.CAPITAL_BUDGET}**",
                    color=0x1e3d52,
                    timestamp=datetime.utcnow()
                )
            )

            opps = await scan_for_opportunities(settings.CAPITAL_BUDGET)

            if opps:
                await channel.send(
                    f"**💡 {len(opps)} Opportunities Found — {datetime.now().strftime('%b %d %H:%M')}**\n"
                    f"Ranked by confidence score. Tap **✅ BUILD THIS** on the one you want."
                )
                for i, opp in enumerate(opps):
                    embed = opportunity_embed(opp, i)
                    view = OpportunityApproveView(opp, bot)
                    await channel.send(embed=embed, view=view)
                    await asyncio.sleep(1)
            else:
                await channel.send("⚠️ Scan returned no results this cycle.")

        except Exception as e:
            logger.error(f"Opportunity scanner error: {e}")

        await asyncio.sleep(interval_minutes * 60)
