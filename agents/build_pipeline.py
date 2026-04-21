"""
OpenClaw — Build Pipeline Agent
Triggered when an opportunity is approved.
Runs the full build sequence: research → content → listing → launch plan.
Posts everything to #build-pipeline ready to copy-paste into Etsy/Gumroad.
"""

import asyncio
import json
import logging
import discord
from datetime import datetime
from ventures.digital_product import (
    research_opportunity,
    generate_product_content,
    generate_listing_pack,
    generate_product_batch,
    generate_launch_strategy
)
from config.settings import settings

logger = logging.getLogger("openclaw.build_pipeline")


def listing_embed(listing: dict) -> discord.Embed:
    """Embed showing the complete ready-to-copy Etsy/Gumroad listing."""
    embed = discord.Embed(
        title=f"🏪 Listing Pack Ready",
        color=0x00f5a0,
        timestamp=datetime.utcnow()
    )

    # Etsy title
    title = listing.get('etsy_title', '')
    if title:
        embed.add_field(name="📝 Etsy Title (copy exactly)", value=f"```{title}```", inline=False)

    # Price
    embed.add_field(name="💰 Price", value=listing.get('etsy_price', '$9'), inline=True)
    embed.add_field(name="🛍️ Gumroad Price", value=listing.get('gumroad_price', '$9'), inline=True)

    # Tags
    tags = listing.get('etsy_tags', [])
    if tags:
        embed.add_field(name="🏷️ Etsy Tags (copy all 13)", value=", ".join(tags), inline=False)

    embed.set_footer(text="OpenClaw Build Pipeline • Full description in thread below")
    return embed


def content_spec_embed(content: dict, product_name: str) -> discord.Embed:
    """Embed showing what to actually build."""
    embed = discord.Embed(
        title=f"🔨 Build Spec: {product_name}",
        description=f"**Format:** {content.get('format', 'N/A')} | **Est. Build Time:** {content.get('build_time_estimate', 'N/A')}",
        color=0xb060ff,
        timestamp=datetime.utcnow()
    )

    sections = content.get('sections', [])
    for i, section in enumerate(sections[:5]):
        embed.add_field(
            name=f"Section {i+1}: {section.get('name', '')}",
            value=section.get('purpose', '') + "\n" + ", ".join(section.get('example_items', [])[:3]),
            inline=False
        )

    tools = content.get('tools_needed', [])
    if tools:
        embed.add_field(name="🛠️ Tools Needed", value="\n".join([f"• {t}" for t in tools]), inline=True)

    bonuses = content.get('bonus_items', [])
    if bonuses:
        embed.add_field(name="🎁 Bonus Items", value="\n".join([f"• {b}" for b in bonuses]), inline=True)

    if content.get('design_direction'):
        embed.add_field(name="🎨 Design Direction", value=content['design_direction'], inline=False)

    if content.get('mockup_description'):
        embed.add_field(name="📸 Thumbnail Concept", value=content['mockup_description'], inline=False)

    embed.set_footer(text="OpenClaw Build Pipeline • Build this, then paste the listing pack into Etsy")
    return embed


def launch_plan_embed(plan: dict) -> discord.Embed:
    """30-day launch roadmap embed."""
    embed = discord.Embed(
        title=f"📅 30-Day Launch Plan → ${settings.REVENUE_TARGET}",
        description=plan.get('strategy_summary', ''),
        color=0xffc944,
        timestamp=datetime.utcnow()
    )

    weeks = ['week_1', 'week_2', 'week_3', 'week_4']
    week_names = ['Week 1', 'Week 2', 'Week 3', 'Week 4']

    for week_key, week_name in zip(weeks, week_names):
        week = plan.get(week_key, {})
        if week:
            val = (
                f"**Focus:** {week.get('focus', '')}\n"
                f"**Listings:** {week.get('listings_to_create', 0)} new\n"
                f"**Spend:** {week.get('budget_spend', '$0')}\n"
                f"**Expected Rev:** {week.get('expected_revenue', 'TBD')}"
            )
            embed.add_field(name=week_name, value=val, inline=True)

    free_channels = plan.get('free_traffic_channels', [])
    if free_channels:
        embed.add_field(
            name="📣 Free Traffic Channels",
            value="\n".join([f"• {c}" for c in free_channels]),
            inline=False
        )

    milestones = []
    if plan.get('milestone_1'): milestones.append(f"🥇 First sale: {plan['milestone_1']}")
    if plan.get('milestone_2'): milestones.append(f"💵 $100: {plan['milestone_2']}")
    if plan.get('milestone_3'): milestones.append(f"🎯 $500: {plan['milestone_3']}")

    if milestones:
        embed.add_field(name="🏁 Milestones", value="\n".join(milestones), inline=False)

    if plan.get('month_2_projection'):
        embed.add_field(name="📈 Month 2 Projection", value=plan['month_2_projection'], inline=False)

    embed.set_footer(text="OpenClaw Build Pipeline • Follow this plan daily")
    return embed


def product_batch_embed(products: list[dict], niche: str) -> discord.Embed:
    """Shows the full 5-product store lineup."""
    embed = discord.Embed(
        title=f"🛒 Store Lineup — {niche}",
        description=f"Build all {len(products)} for maximum store conversion. Buyers browse multiple listings.",
        color=0x00c8f0,
        timestamp=datetime.utcnow()
    )

    total_potential = 0
    for i, p in enumerate(products):
        embed.add_field(
            name=f"Product {i+1}: {p.get('name', 'Unknown')}",
            value=(
                f"{p.get('type', '')} • {p.get('price', '$9')}\n"
                f"{p.get('one_line_description', '')}\n"
                f"🔍 `{p.get('primary_keyword', '')}`"
            ),
            inline=False
        )

    embed.set_footer(text="OpenClaw • Build products in order — list #1 first, get feedback, iterate")
    return embed


async def run_build_pipeline(bot, channel_id: int):
    """
    Monitors approved_opportunities and runs the full build sequence.
    Posts everything to #build-pipeline as copy-paste ready packages.
    """
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)

    if not channel:
        logger.error(f"Build pipeline channel {channel_id} not found")
        return

    if not hasattr(bot, 'approved_opportunities'):
        bot.approved_opportunities = []
    if not hasattr(bot, 'built_opportunities'):
        bot.built_opportunities = set()

    logger.info("Build Pipeline ready — monitoring for approved opportunities")

    while not bot.is_closed():
        try:
            for opp in bot.approved_opportunities:
                niche = opp.get('niche', '')
                if niche and niche not in bot.built_opportunities:
                    bot.built_opportunities.add(niche)

                    logger.info(f"Starting build pipeline for: {niche}")

                    # ── Stage 1: Deep Research ────────────────────────────
                    await channel.send(embed=discord.Embed(
                        title=f"⚡ Build Pipeline Started: {niche}",
                        description="Running 4-stage build sequence. Everything will be copy-paste ready.",
                        color=0x00c8f0,
                        timestamp=datetime.utcnow()
                    ))

                    await channel.send(embed=discord.Embed(
                        description="**Stage 1/4:** Researching the opportunity in depth...",
                        color=0x1e3d52
                    ))

                    research = await research_opportunity(niche, settings.CAPITAL_BUDGET)

                    if not research:
                        await channel.send("❌ Research failed. Try `/build` again.")
                        continue

                    # Post research summary
                    r_embed = discord.Embed(
                        title=f"📊 Research Complete: {research.get('product_name', niche)}",
                        color=0x00f5a0,
                        timestamp=datetime.utcnow()
                    )
                    r_embed.add_field(name="Product", value=research.get('product_name', 'N/A'), inline=True)
                    r_embed.add_field(name="Type", value=research.get('product_type', 'N/A'), inline=True)
                    r_embed.add_field(name="Price", value=research.get('price_point', 'N/A'), inline=True)
                    r_embed.add_field(name="Buyer", value=research.get('buyer_persona', 'N/A'), inline=False)
                    r_embed.add_field(name="Pain Point", value=research.get('pain_point', 'N/A'), inline=False)
                    r_embed.add_field(name="Monthly Potential", value=research.get('monthly_potential', 'N/A'), inline=True)
                    await channel.send(embed=r_embed)
                    await asyncio.sleep(2)

                    # ── Stage 2: Content Spec ─────────────────────────────
                    await channel.send(embed=discord.Embed(
                        description="**Stage 2/4:** Generating product content spec...",
                        color=0x1e3d52
                    ))

                    content = await generate_product_content(research)
                    if content:
                        await channel.send(embed=content_spec_embed(content, research.get('product_name', niche)))
                    await asyncio.sleep(2)

                    # ── Stage 3: Listing Pack ─────────────────────────────
                    await channel.send(embed=discord.Embed(
                        description="**Stage 3/4:** Generating listing pack (Etsy + Gumroad copy)...",
                        color=0x1e3d52
                    ))

                    listing = await generate_listing_pack(research, content or {})
                    if listing:
                        await channel.send(embed=listing_embed(listing))

                        # Post full Etsy description in a follow-up message (too long for embed)
                        desc = listing.get('etsy_description', '')
                        if desc:
                            # Split into chunks if needed
                            chunks = [desc[i:i+1900] for i in range(0, len(desc), 1900)]
                            await channel.send(f"**📋 Full Etsy Description (copy-paste ready):**")
                            for chunk in chunks:
                                await channel.send(f"```{chunk}```")

                        # Social posts
                        social_embed = discord.Embed(
                            title="📱 Social Media Posts",
                            color=0xff4fa3,
                            timestamp=datetime.utcnow()
                        )
                        if listing.get('tiktok_hook'):
                            social_embed.add_field(name="🎬 TikTok Hook", value=listing['tiktok_hook'], inline=False)
                        if listing.get('instagram_caption'):
                            social_embed.add_field(name="📸 Instagram", value=listing['instagram_caption'][:300], inline=False)
                        if listing.get('reddit_pitch'):
                            social_embed.add_field(name="🔴 Reddit", value=listing['reddit_pitch'], inline=False)
                        await channel.send(embed=social_embed)

                    await asyncio.sleep(2)

                    # ── Stage 4: Launch Plan ──────────────────────────────
                    await channel.send(embed=discord.Embed(
                        description="**Stage 4/4:** Building your 30-day launch plan...",
                        color=0x1e3d52
                    ))

                    # Product batch (full store lineup)
                    products = await generate_product_batch(niche, count=5)
                    if products:
                        await channel.send(embed=product_batch_embed(products, niche))

                    # 30-day plan
                    plan = await generate_launch_strategy(niche, settings.CAPITAL_BUDGET)
                    if plan:
                        await channel.send(embed=launch_plan_embed(plan))

                    # ── Done ──────────────────────────────────────────────
                    await channel.send(embed=discord.Embed(
                        title="✅ Build Pipeline Complete!",
                        description=(
                            f"**Everything is ready for: {niche}**\n\n"
                            f"**Your next 3 actions:**\n"
                            f"1. Build the product using the spec above (tools: Notion/Canva/Sheets — all free)\n"
                            f"2. Create your Etsy shop at etsy.com/sell (free, $0.20/listing)\n"
                            f"3. Copy-paste the listing pack above into your first Etsy listing\n\n"
                            f"Type `/revenue add [product] [amount]` when you make your first sale 💰"
                        ),
                        color=0x00f5a0,
                        timestamp=datetime.utcnow()
                    ))

                    # Store built opportunity on bot
                    if not hasattr(bot, 'active_ventures'):
                        bot.active_ventures = []
                    bot.active_ventures.append({
                        'niche': niche,
                        'research': research,
                        'listing': listing,
                        'plan': plan,
                        'started': datetime.now().isoformat()
                    })

        except Exception as e:
            logger.error(f"Build pipeline error: {e}")
            if channel:
                await channel.send(f"❌ Build pipeline error: {e}")

        await asyncio.sleep(15)
