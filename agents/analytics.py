"""
OpenClaw — Sales Analytics Agent
Tracks what's actually selling on Etsy using public data + your own store.
Finds winning products, spots trends early, recommends what to build next.

Data sources:
- Your own Etsy sales (via API)
- Your Gumroad sales (via API)  
- Public Etsy search data (trending keywords)
- Claude analysis of market signals

Posts weekly intelligence reports to #revenue.
"""

import asyncio
import logging
import discord
from datetime import datetime, timedelta
from utils.claude import think_json, think
from config.settings import settings

logger = logging.getLogger("openclaw.analytics")

SYSTEM = """You are OpenClaw's Market Intelligence Analyst.
You analyze sales data and market signals to find winning opportunities.
You give specific, data-driven recommendations — not generic advice.
Always respond with valid JSON only."""


async def analyze_etsy_market(niche: str) -> dict:
    """
    Uses Claude to analyze what's currently selling in a niche.
    Based on public Etsy search patterns and market intelligence.
    """
    import json
    prompt = f"""Analyze the current Etsy market for: {niche}

Based on what you know about Etsy search patterns, buyer behavior, and
digital product trends as of {datetime.now().strftime('%B %Y')}:

Return JSON:
{{
  "niche": "{niche}",
  "market_temperature": "hot | warm | cooling | cold",
  "estimated_monthly_searches": "e.g. 50,000-100,000",
  "top_selling_product_types": [
    {{"type": "Product type", "avg_price": "$X", "competition": "low/medium/high", "opportunity": "description"}}
  ],
  "trending_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "underserved_gaps": ["Gap 1 — what's missing", "Gap 2", "Gap 3"],
  "price_sweet_spots": ["$7-9 for X", "$12-15 for Y", "$20-25 for Z"],
  "buyer_demographics": "Who is buying and why",
  "seasonal_notes": "Any seasonal patterns to know about",
  "competition_analysis": "Overview of who dominates and where gaps are",
  "quick_win": "The single fastest path to a sale in this niche right now",
  "confidence": 80
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=2000)
    try:
        import json as j
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return j.loads(clean)
    except:
        return {}


async def analyze_own_performance(revenue_log: dict, ventures: list) -> dict:
    """Analyzes your own store performance and gives recommendations."""
    import json as j

    if not revenue_log and not ventures:
        return {
            "status": "pre_revenue",
            "message": "No sales yet — focus on getting first listing live",
            "priority_action": "Complete your first Etsy listing today"
        }

    total = sum(revenue_log.values()) if revenue_log else 0
    top_product = max(revenue_log.items(), key=lambda x: x[1])[0] if revenue_log else None

    prompt = f"""Analyze this digital product store performance:

Revenue log: {j.dumps(revenue_log)}
Total revenue: ${total:.2f}
Target: ${settings.REVENUE_TARGET:.0f} in {settings.TARGET_DAYS} days
Active niches: {[v.get('niche') for v in ventures if v.get('niche')]}
Top product: {top_product}

Give specific, actionable intelligence:

Return JSON:
{{
  "performance_grade": "A/B/C/D/F",
  "revenue_velocity": "on track | ahead | behind",
  "top_performer": "{top_product or 'none yet'}",
  "what_is_working": "Specific observation",
  "what_to_fix": "Specific action to take",
  "next_product_to_build": "Specific recommendation based on what's selling",
  "pricing_recommendation": "Should you raise/lower prices?",
  "traffic_recommendation": "Where to focus traffic efforts",
  "days_to_target_estimate": 30,
  "monthly_run_rate": ${total:.2f},
  "priority_actions": [
    "Action 1 — most impactful",
    "Action 2",
    "Action 3"
  ]
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=1500)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return j.loads(clean)
    except:
        return {"status": "analysis_failed", "total": total}


def analytics_embed(analysis: dict, title: str = "📊 Market Intelligence") -> discord.Embed:
    """Rich embed for analytics report."""

    temp = analysis.get("market_temperature", "")
    temp_colors = {"hot": 0xff4500, "warm": 0xffc944, "cooling": 0x00c8f0, "cold": 0x718096}
    color = temp_colors.get(temp, 0x00c8f0)

    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=datetime.utcnow()
    )

    def sf(name, value, inline=False):
        if value:
            v = str(value)
            embed.add_field(name=name[:256], value=v[:1024] or "N/A", inline=inline)

    # Market analysis
    if analysis.get("market_temperature"):
        temp_emoji = {"hot": "🔥", "warm": "☀️", "cooling": "🌤", "cold": "❄️"}.get(temp, "📊")
        sf("🌡️ Market Temp", f"{temp_emoji} {temp.upper()} — {analysis.get('estimated_monthly_searches', 'N/A')} searches/mo", inline=True)

    if analysis.get("confidence"):
        sf("🎯 Confidence", f"{analysis['confidence']}/100", inline=True)

    if analysis.get("quick_win"):
        sf("⚡ Quick Win", analysis["quick_win"])

    gaps = analysis.get("underserved_gaps", [])
    if gaps:
        sf("🕳️ Market Gaps", "\n".join([f"• {g}" for g in gaps[:3]]))

    keywords = analysis.get("trending_keywords", [])
    if keywords:
        sf("🔍 Hot Keywords", " • ".join(keywords[:5]))

    prices = analysis.get("price_sweet_spots", [])
    if prices:
        sf("💰 Price Sweet Spots", "\n".join([f"• {p}" for p in prices[:3]]))

    # Performance analysis
    if analysis.get("performance_grade"):
        sf("📈 Grade", analysis["performance_grade"], inline=True)
    if analysis.get("revenue_velocity"):
        sf("🚀 Velocity", analysis["revenue_velocity"], inline=True)

    if analysis.get("priority_actions"):
        actions = analysis["priority_actions"]
        sf("✅ Priority Actions", "\n".join([f"{i+1}. {a}" for i, a in enumerate(actions[:3])]))

    if analysis.get("next_product_to_build"):
        sf("🏗️ Build Next", analysis["next_product_to_build"])

    sellers = analysis.get("top_selling_product_types", [])
    if sellers:
        seller_text = "\n".join([
            f"• {s.get('type','?')} — {s.get('avg_price','?')} — {s.get('competition','?')} competition"
            for s in sellers[:3]
        ])
        sf("🏆 Top Selling Types", seller_text)

    embed.set_footer(text="OpenClaw Analytics • Updated live")
    return embed


async def run_analytics_agent(bot, channel_id: int):
    """
    Posts weekly market intelligence reports.
    Also responds to /analytics command.
    """
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        logger.error(f"Analytics channel {channel_id} not found")
        return

    logger.info("Analytics agent running")

    while not bot.is_closed():
        try:
            ventures = getattr(bot, 'active_ventures', [])
            revenue  = getattr(bot, 'revenue_log', {})

            if ventures:
                # Post performance analysis
                perf = await analyze_own_performance(revenue, ventures)
                embed = analytics_embed(perf, "📊 Weekly Performance Report")
                await channel.send(embed=embed)

                # Post market analysis for each active niche
                for venture in ventures[:2]:  # Max 2 to avoid spam
                    niche = venture.get('niche', '')
                    if niche:
                        market = await analyze_etsy_market(niche)
                        if market:
                            embed = analytics_embed(market, f"🔍 Market Intel: {niche[:50]}")
                            await channel.send(embed=embed)
                        await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Analytics error: {e}")

        # Run weekly
        await asyncio.sleep(7 * 24 * 60 * 60)
