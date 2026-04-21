"""
OpenClaw — Revenue Tracker + Reinvestment Engine
Tracks every sale, calculates progress toward $500 goal,
and tells you exactly how to reinvest each dollar earned.
"""

import asyncio
import logging
import discord
from datetime import datetime
from config.settings import settings

logger = logging.getLogger("openclaw.revenue")


def revenue_embed(bot) -> discord.Embed:
    revenue_log = getattr(bot, 'revenue_log', {})
    total = sum(revenue_log.values())
    target = settings.REVENUE_TARGET
    pct = min(int((total / target) * 100), 100)

    # Progress bar
    filled = int(pct / 10)
    bar = "█" * filled + "░" * (10 - filled)

    color = 0x00f5a0 if pct >= 80 else 0xffc944 if pct >= 40 else 0x00c8f0

    embed = discord.Embed(
        title="💰 Revenue Dashboard",
        color=color,
        timestamp=datetime.utcnow()
    )

    embed.add_field(
        name=f"Progress to ${int(target):,}",
        value=f"`{bar}` **{pct}%**\n**${total:,.2f}** of **${target:,.0f}**",
        inline=False
    )

    if revenue_log:
        for product, amount in sorted(revenue_log.items(), key=lambda x: x[1], reverse=True):
            embed.add_field(name=product, value=f"${amount:,.2f}", inline=True)
    else:
        embed.add_field(
            name="No sales yet",
            value=(
                "Use `/revenue add [product] [amount]` after each sale.\n"
                "Example: `/revenue add \"Notion Budget Tracker\" 9.00`"
            ),
            inline=False
        )

    # Reinvestment advice based on total earned
    if total >= 50:
        reinvest = total * 0.7
        embed.add_field(
            name="📈 Reinvestment Recommendation",
            value=(
                f"You have **${total:.2f}** earned.\n"
                f"• **${reinvest * 0.6:.2f}** → Etsy promoted listings\n"
                f"• **${reinvest * 0.3:.2f}** → Pinterest ads\n"
                f"• **${reinvest * 0.1:.2f}** → New listing fees\n"
                f"• Keep **${total * 0.3:.2f}** as profit"
            ),
            inline=False
        )

    remaining = max(0, target - total)
    if remaining > 0:
        embed.add_field(
            name="🎯 To Hit Target",
            value=f"**${remaining:,.2f}** more needed",
            inline=True
        )

    embed.set_footer(text=f"OpenClaw Revenue Tracker • {settings.TARGET_DAYS}-day goal: ${settings.REVENUE_TARGET:,.0f}")
    return embed


async def run_revenue_tracker(bot, channel_id: int):
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        logger.error(f"Revenue channel {channel_id} not found")
        return

    if not hasattr(bot, 'revenue_log'):
        bot.revenue_log = {}

    logger.info("Revenue Tracker running")
    await channel.send(embed=revenue_embed(bot))

    while not bot.is_closed():
        await asyncio.sleep(settings.REVENUE_INTERVAL * 60)
        try:
            await channel.send(embed=revenue_embed(bot))
        except Exception as e:
            logger.error(f"Revenue tracker error: {e}")
