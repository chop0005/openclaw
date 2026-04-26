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

# Discord hard limits
FIELD_MAX  = 1024
TITLE_MAX  = 256
DESC_MAX   = 4096

def trunc(text: str, limit: int = FIELD_MAX) -> str:
    """Safely truncate any string to Discord's field limit."""
    if not text:
        return "N/A"
    text = str(text)
    return text[:limit - 3] + "..." if len(text) > limit else text


def safe_field(embed: discord.Embed, name: str, value: str, inline: bool = False):
    """Add a field, guaranteed within Discord limits."""
    embed.add_field(
        name=trunc(name, 256),
        value=trunc(value, FIELD_MAX) or "N/A",
        inline=inline
    )


def listing_embed(listing: dict) -> discord.Embed:
    embed = discord.Embed(
        title="🏪 Listing Pack Ready",
        color=0x00f5a0,
        timestamp=datetime.utcnow()
    )

    title = listing.get('etsy_title', '')
    if title:
        safe_field(embed, "📝 Etsy Title (copy exactly)", f"```{trunc(title, 950)}```")

    embed.add_field(name="💰 Etsy Price",    value=listing.get('etsy_price', '$9'),    inline=True)
    embed.add_field(name="🛍️ Gumroad Price", value=listing.get('gumroad_price', '$9'), inline=True)

    tags = listing.get('etsy_tags', [])
    if tags:
        safe_field(embed, "🏷️ Etsy Tags (all 13)", ", ".join(tags))

    embed.set_footer(text="OpenClaw Build Pipeline • Full description posted below")
    return embed


def content_spec_embed(content: dict, product_name: str) -> discord.Embed:
    embed = discord.Embed(
        title=trunc(f"🔨 Build Spec: {product_name}", TITLE_MAX),
        description=trunc(
            f"**Format:** {content.get('format', 'N/A')} | **Est. Build Time:** {content.get('build_time_estimate', 'N/A')}",
            DESC_MAX
        ),
        color=0xb060ff,
        timestamp=datetime.utcnow()
    )

    sections = content.get('sections', [])
    for i, section in enumerate(sections[:4]):  # max 4 sections
        purpose   = section.get('purpose', '')
        examples  = ", ".join(section.get('example_items', [])[:3])
        value     = f"{purpose}\n{examples}" if examples else purpose
        safe_field(embed, f"Section {i+1}: {section.get('name', '')}", value)

    tools = content.get('tools_needed', [])
    if tools:
        safe_field(embed, "🛠️ Tools Needed", "\n".join([f"• {t}" for t in tools[:6]]), inline=True)

    bonuses = content.get('bonus_items', [])
    if bonuses:
        safe_field(embed, "🎁 Bonus Items", "\n".join([f"• {b}" for b in bonuses[:5]]), inline=True)

    if content.get('design_direction'):
        safe_field(embed, "🎨 Design Direction", content['design_direction'])

    if content.get('mockup_description'):
        safe_field(embed, "📸 Thumbnail Concept", content['mockup_description'])

    embed.set_footer(text="OpenClaw Build Pipeline • Build this, then paste the listing pack into Etsy")
    return embed


def launch_plan_embed(plan: dict) -> discord.Embed:
    embed = discord.Embed(
        title=trunc(f"📅 30-Day Launch Plan → ${settings.REVENUE_TARGET:.0f}", TITLE_MAX),
        description=trunc(plan.get('strategy_summary', ''), DESC_MAX),
        color=0xffc944,
        timestamp=datetime.utcnow()
    )

    weeks = [('week_1','Week 1'), ('week_2','Week 2'), ('week_3','Week 3'), ('week_4','Week 4')]
    for week_key, week_name in weeks:
        w = plan.get(week_key, {})
        if w:
            val = (
                f"**{trunc(w.get('focus',''), 200)}**\n"
                f"Listings: {w.get('listings_to_create', 0)} | "
                f"Spend: {w.get('budget_spend','$0')} | "
                f"Rev: {w.get('expected_revenue','TBD')}"
            )
            safe_field(embed, week_name, val, inline=True)

    free_channels = plan.get('free_traffic_channels', [])
    if free_channels:
        safe_field(embed, "📣 Free Traffic", "\n".join([f"• {trunc(c,150)}" for c in free_channels[:4]]))

    milestones = []
    if plan.get('milestone_1'): milestones.append(f"🥇 First sale: {plan['milestone_1']}")
    if plan.get('milestone_2'): milestones.append(f"💵 $100: {plan['milestone_2']}")
    if plan.get('milestone_3'): milestones.append(f"🎯 $500: {plan['milestone_3']}")
    if milestones:
        safe_field(embed, "🏁 Milestones", "\n".join(milestones))

    if plan.get('month_2_projection'):
        safe_field(embed, "📈 Month 2 Projection", plan['month_2_projection'])

    embed.set_footer(text="OpenClaw Build Pipeline • Follow this plan daily")
    return embed


def product_batch_embed(products: list, niche: str) -> discord.Embed:
    embed = discord.Embed(
        title=trunc(f"🛒 Store Lineup — {niche}", TITLE_MAX),
        description=f"Build all {len(products)} for maximum store conversion.",
        color=0x00c8f0,
        timestamp=datetime.utcnow()
    )
    for i, p in enumerate(products):
        val = (
            f"{p.get('type','')} • {p.get('price','$9')}\n"
            f"{trunc(p.get('one_line_description',''), 150)}\n"
            f"🔍 `{p.get('primary_keyword','')}`"
        )
        safe_field(embed, f"Product {i+1}: {p.get('name','Unknown')}", val)

    embed.set_footer(text="OpenClaw • List product #1 first, get feedback, then add the rest")
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

                    # ── Start ─────────────────────────────────────────
                    await channel.send(embed=discord.Embed(
                        title=trunc(f"⚡ Build Pipeline Started: {niche}", TITLE_MAX),
                        description="Running 4-stage build. Everything will be copy-paste ready.",
                        color=0x00c8f0,
                        timestamp=datetime.utcnow()
                    ))

                    # ── Stage 1: Research ─────────────────────────────
                    await channel.send(embed=discord.Embed(
                        description="**Stage 1/4:** Deep research...",
                        color=0x1e3d52
                    ))

                    research = await research_opportunity(niche, settings.CAPITAL_BUDGET)
                    if not research:
                        await channel.send("❌ Research failed. Try `/build` again.")
                        continue

                    r_embed = discord.Embed(
                        title=trunc(f"📊 Research: {research.get('product_name', niche)}", TITLE_MAX),
                        color=0x00f5a0,
                        timestamp=datetime.utcnow()
                    )
                    safe_field(r_embed, "Product",          research.get('product_name','N/A'),    inline=True)
                    safe_field(r_embed, "Type",             research.get('product_type','N/A'),    inline=True)
                    safe_field(r_embed, "Price",            research.get('price_point','N/A'),     inline=True)
                    safe_field(r_embed, "Buyer",            research.get('buyer_persona','N/A'))
                    safe_field(r_embed, "Pain Point",       research.get('pain_point','N/A'))
                    safe_field(r_embed, "Monthly Potential",research.get('monthly_potential','N/A'),inline=True)
                    await channel.send(embed=r_embed)
                    await asyncio.sleep(2)

                    # ── Stage 2: Content Spec ─────────────────────────
                    await channel.send(embed=discord.Embed(
                        description="**Stage 2/4:** Generating product content spec...",
                        color=0x1e3d52
                    ))
                    content = await generate_product_content(research)
                    if content:
                        await channel.send(embed=content_spec_embed(content, research.get('product_name', niche)))
                    await asyncio.sleep(2)

                    # ── Stage 3: Listing Pack ─────────────────────────
                    await channel.send(embed=discord.Embed(
                        description="**Stage 3/4:** Generating Etsy + Gumroad listing pack...",
                        color=0x1e3d52
                    ))
                    listing = await generate_listing_pack(research, content or {})
                    if listing:
                        await channel.send(embed=listing_embed(listing))

                        # Post full description as plain message (no embed limit)
                        desc = listing.get('etsy_description', '')
                        if desc:
                            await channel.send("**📋 Full Etsy Description — copy this exactly:**")
                            # Split into 1900-char chunks to stay under Discord message limit
                            chunks = [desc[i:i+1900] for i in range(0, len(desc), 1900)]
                            for chunk in chunks:
                                await channel.send(f"```{chunk}```")

                        # Social posts
                        social = discord.Embed(title="📱 Social Media Posts", color=0xff4fa3, timestamp=datetime.utcnow())
                        if listing.get('tiktok_hook'):
                            safe_field(social, "🎬 TikTok Hook",      listing['tiktok_hook'])
                        if listing.get('instagram_caption'):
                            safe_field(social, "📸 Instagram",        listing['instagram_caption'])
                        if listing.get('reddit_pitch'):
                            safe_field(social, "🔴 Reddit",           listing['reddit_pitch'])
                        if listing.get('pinterest_caption'):
                            safe_field(social, "📌 Pinterest",        listing['pinterest_caption'])
                        await channel.send(embed=social)

                    await asyncio.sleep(2)

                    # ── Stage 4: Launch Plan ──────────────────────────
                    await channel.send(embed=discord.Embed(
                        description="**Stage 4/4:** Building your 30-day launch plan...",
                        color=0x1e3d52
                    ))

                    products = await generate_product_batch(niche, count=5)
                    if products:
                        await channel.send(embed=product_batch_embed(products, niche))

                    plan = await generate_launch_strategy(niche, settings.CAPITAL_BUDGET)
                    if plan:
                        await channel.send(embed=launch_plan_embed(plan))

                    # ── Done ──────────────────────────────────────────
                    await channel.send(embed=discord.Embed(
                        title="✅ Build Complete!",
                        description=(
                            f"**{niche} — everything is ready.**\n\n"
                            f"**Your next 3 actions:**\n"
                            f"1. Build the product using the spec above (Notion/Canva/Sheets — free)\n"
                            f"2. Open your Etsy shop at etsy.com/sell ($0 to open, $0.20/listing)\n"
                            f"3. Copy-paste the listing pack above into your first listing\n\n"
                            f"Type `/revenue add \"product name\" 9.00` when you get your first sale 💰"
                        ),
                        color=0x00f5a0,
                        timestamp=datetime.utcnow()
                    ))

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
