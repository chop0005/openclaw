"""
OpenClaw — Build Pipeline Agent v3
All external imports are lazy (inside functions) so missing files
never crash the bot at startup. Fully self-contained startup.
"""

import asyncio
import logging
import discord
from datetime import datetime
from config.settings import settings

logger = logging.getLogger("openclaw.build_pipeline")

FIELD_MAX = 1024
TITLE_MAX = 256
DESC_MAX  = 4096

def trunc(text, limit=FIELD_MAX):
    if not text: return "N/A"
    s = str(text)
    return s[:limit-3]+"..." if len(s) > limit else s

def sf(embed, name, value, inline=False):
    embed.add_field(
        name=trunc(name, 256),
        value=trunc(value, FIELD_MAX) or "N/A",
        inline=inline
    )


async def run_build_pipeline(bot, channel_id: int):
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        logger.error(f"Build pipeline channel {channel_id} not found")
        return

    if not hasattr(bot, 'approved_opportunities'): bot.approved_opportunities = []
    if not hasattr(bot, 'built_opportunities'):    bot.built_opportunities = set()
    if not hasattr(bot, 'active_ventures'):        bot.active_ventures = []

    logger.info("Build Pipeline ready")

    while not bot.is_closed():
        try:
            for opp in bot.approved_opportunities:
                niche = opp.get('niche', '')
                if not niche or niche in bot.built_opportunities:
                    continue

                bot.built_opportunities.add(niche)
                logger.info(f"Pipeline starting: {niche}")

                # ── Lazy imports — safe even if files missing ─────────
                try:
                    from ventures.digital_product import (
                        research_opportunity, generate_listing_pack,
                        generate_product_batch, generate_launch_strategy
                    )
                except ImportError as e:
                    await channel.send(f"❌ Import error: {e}")
                    continue

                # ── Start ─────────────────────────────────────────────
                await channel.send(embed=discord.Embed(
                    title=trunc(f"⚡ Pipeline: {niche}", TITLE_MAX),
                    description="Running build sequence. Everything will be copy-paste ready.",
                    color=0x00c8f0, timestamp=datetime.utcnow()
                ))

                # ── Stage 1: Research ─────────────────────────────────
                await channel.send(embed=discord.Embed(
                    description="**Stage 1/5:** Deep research...", color=0x1e3d52
                ))
                research = await research_opportunity(niche, settings.CAPITAL_BUDGET)
                if not research:
                    await channel.send("❌ Research failed. Try `/build` again.")
                    continue

                r_embed = discord.Embed(
                    title=trunc(f"📊 Research: {research.get('product_name', niche)}", TITLE_MAX),
                    color=0x00f5a0, timestamp=datetime.utcnow()
                )
                sf(r_embed, "Product",    research.get('product_name','N/A'), inline=True)
                sf(r_embed, "Type",       research.get('product_type','N/A'), inline=True)
                sf(r_embed, "Price",      research.get('price_point','$9'),   inline=True)
                sf(r_embed, "Buyer",      research.get('buyer_persona','N/A'))
                sf(r_embed, "Pain Point", research.get('pain_point','N/A'))
                sf(r_embed, "Potential",  research.get('monthly_potential','N/A'), inline=True)
                await channel.send(embed=r_embed)
                await asyncio.sleep(2)

                # ── Stage 2: Generate Product ─────────────────────────
                await channel.send(embed=discord.Embed(
                    description="**Stage 2/5:** Generating the product (PDF or Notion)...",
                    color=0x1e3d52
                ))
                product_result = {'type': 'pdf', 'summary': '', 'ready_to_list': False, 'result': {}}
                try:
                    from ventures.product_generator import generate_product
                    product_result = await generate_product(research, niche)
                    ptype = product_result.get('type', 'pdf').upper()
                    prod_embed = discord.Embed(
                        title=trunc(f"{'📄' if ptype=='PDF' else '📋'} {ptype} Generated", TITLE_MAX),
                        description=trunc(product_result.get('summary', ''), DESC_MAX),
                        color=0x00f5a0 if ptype == "PDF" else 0xb060ff,
                        timestamp=datetime.utcnow()
                    )
                    structure = product_result.get('structure', {})
                    if structure.get('sections'):
                        sf(prod_embed, "Sections", "\n".join([f"• {s}" for s in structure['sections'][:5]]))
                    result_data = product_result.get('result', {})
                    if ptype == "PDF" and result_data.get('filename'):
                        sf(prod_embed, "File", result_data.get('filename','N/A'), inline=True)
                        sf(prod_embed, "Pages", str(result_data.get('page_count',0)), inline=True)
                    await channel.send(embed=prod_embed)
                except ImportError:
                    await channel.send(embed=discord.Embed(
                        description="⚠️ Product generator not available — skipping to listing.",
                        color=0xff7733
                    ))
                await asyncio.sleep(2)

                # ── Stage 3: Listing Pack ─────────────────────────────
                await channel.send(embed=discord.Embed(
                    description="**Stage 3/5:** Generating Etsy + Gumroad listing pack...",
                    color=0x1e3d52
                ))
                listing = await generate_listing_pack(research, {})
                if listing:
                    l_embed = discord.Embed(
                        title="🏪 Listing Pack Ready",
                        color=0x00f5a0, timestamp=datetime.utcnow()
                    )
                    sf(l_embed, "📝 Etsy Title", f"```{trunc(listing.get('etsy_title',''), 950)}```")
                    sf(l_embed, "💰 Price", listing.get('etsy_price','$9'), inline=True)
                    sf(l_embed, "🛍️ Gumroad", listing.get('gumroad_price','$9'), inline=True)
                    tags = listing.get('etsy_tags', [])
                    if tags:
                        sf(l_embed, "🏷️ Tags (13)", ", ".join(tags))
                    await channel.send(embed=l_embed)

                    desc = listing.get('etsy_description', '')
                    if desc:
                        await channel.send("**📋 Full Etsy Description — copy exactly:**")
                        for chunk in [desc[i:i+1900] for i in range(0, len(desc), 1900)]:
                            await channel.send(f"```{chunk}```")

                    s_embed = discord.Embed(title="📱 Social Posts", color=0xff4fa3, timestamp=datetime.utcnow())
                    if listing.get('tiktok_hook'):       sf(s_embed, "🎬 TikTok",    listing['tiktok_hook'])
                    if listing.get('instagram_caption'): sf(s_embed, "📸 Instagram", listing['instagram_caption'])
                    if listing.get('reddit_pitch'):      sf(s_embed, "🔴 Reddit",    listing['reddit_pitch'])
                    if listing.get('pinterest_caption'): sf(s_embed, "📌 Pinterest", listing['pinterest_caption'])
                    await channel.send(embed=s_embed)

                await asyncio.sleep(2)

                # ── Stage 4: Etsy Approval ────────────────────────────
                await channel.send(embed=discord.Embed(
                    description="**Stage 4/5:** Etsy listing ready for approval...",
                    color=0x1e3d52
                ))
                if listing:
                    listing_data = {
                        "title":       listing.get('etsy_title', research.get('product_name', niche))[:140],
                        "description": listing.get('etsy_description', ''),
                        "price":       float(listing.get('etsy_price', '$9').replace('$','')),
                        "tags":        listing.get('etsy_tags', [])[:13],
                    }

                    # Etsy buttons (lazy import)
                    try:
                        from ventures.etsy_manager import EtsyApprovalView, listing_approval_embed, EtsyClient, ETSY_SETUP_GUIDE
                        etsy = EtsyClient()
                        if not etsy.is_configured():
                            await channel.send(f"⚠️ **Etsy not configured yet.**\n{ETSY_SETUP_GUIDE}")
                        approval_embed = listing_approval_embed(listing_data, product_result)
                        view = EtsyApprovalView(listing_data, product_result, bot)
                        await channel.send(embed=approval_embed, view=view)
                    except ImportError:
                        await channel.send("⚠️ Etsy manager not available — listing data shown above.")

                    # Gumroad buttons (lazy import)
                    try:
                        from ventures.gumroad_manager import GumroadApprovalView, GumroadClient, GUMROAD_SETUP
                        gr_embed = discord.Embed(
                            title="📦 Also list on Gumroad?",
                            description=(
                                f"**{research.get('product_name', niche)}** — {listing.get('etsy_price','$9')}\n"
                                "Gumroad = zero fees, instant payout, global reach."
                            ),
                            color=0xff90e8, timestamp=datetime.utcnow()
                        )
                        gr_view = GumroadApprovalView(
                            {'niche': niche, 'product_name': research.get('product_name', niche)},
                            {
                                'title':               listing.get('etsy_title', research.get('product_name', niche))[:255],
                                'gumroad_description': listing.get('gumroad_pitch', listing.get('etsy_description',''))[:1000],
                                'price':               float(listing.get('etsy_price','9').replace('$','')),
                                'tags':                listing.get('etsy_tags', [])[:10],
                            },
                            bot
                        )
                        await channel.send(embed=gr_embed, view=gr_view)
                    except ImportError:
                        pass  # Gumroad not available yet — silent skip

                await asyncio.sleep(2)

                # ── Stage 5: Store Lineup + Launch Plan ───────────────
                await channel.send(embed=discord.Embed(
                    description="**Stage 5/5:** Store lineup + 30-day plan...",
                    color=0x1e3d52
                ))

                products = await generate_product_batch(niche, count=5)
                if products:
                    p_embed = discord.Embed(
                        title=trunc(f"🛒 Store Lineup — {niche}", TITLE_MAX),
                        description=f"Build all {len(products)} for max conversion.",
                        color=0x00c8f0, timestamp=datetime.utcnow()
                    )
                    for i, p in enumerate(products):
                        sf(p_embed,
                           f"#{i+1}: {p.get('name','Unknown')}",
                           f"{p.get('type','')} • {p.get('price','$9')}\n"
                           f"{trunc(p.get('one_line_description',''),150)}\n"
                           f"🔍 `{p.get('primary_keyword','')}`"
                        )
                    await channel.send(embed=p_embed)

                plan = await generate_launch_strategy(niche, settings.CAPITAL_BUDGET)
                if plan:
                    plan_embed = discord.Embed(
                        title=trunc(f"📅 30-Day Plan → ${settings.REVENUE_TARGET:.0f}", TITLE_MAX),
                        description=trunc(plan.get('strategy_summary',''), DESC_MAX),
                        color=0xffc944, timestamp=datetime.utcnow()
                    )
                    for wk, wn in [('week_1','Week 1'),('week_2','Week 2'),('week_3','Week 3'),('week_4','Week 4')]:
                        w = plan.get(wk, {})
                        if w:
                            sf(plan_embed, wn,
                               f"**{trunc(w.get('focus',''),120)}**\n"
                               f"Lists: {w.get('listings_to_create',0)} | "
                               f"Rev: {w.get('expected_revenue','TBD')}",
                               inline=True
                            )
                    channels_str = "\n".join([f"• {trunc(c,100)}" for c in plan.get('free_traffic_channels',[])[:4]])
                    if channels_str: sf(plan_embed, "📣 Free Traffic", channels_str)
                    milestones = []
                    if plan.get('milestone_1'): milestones.append(f"🥇 {plan['milestone_1']}")
                    if plan.get('milestone_2'): milestones.append(f"💵 {plan['milestone_2']}")
                    if plan.get('milestone_3'): milestones.append(f"🎯 {plan['milestone_3']}")
                    if milestones: sf(plan_embed, "🏁 Milestones", "\n".join(milestones))
                    await channel.send(embed=plan_embed)

                # ── Done ──────────────────────────────────────────────
                await channel.send(embed=discord.Embed(
                    title="✅ Build Complete!",
                    description=(
                        f"**{niche} — everything is ready.**\n\n"
                        f"**Your next 3 actions:**\n"
                        f"1. Build the product using the spec above\n"
                        f"2. Upload to Etsy + Gumroad using buttons above\n"
                        f"3. Post the social content to start driving traffic\n\n"
                        f"Type `/revenue add \"product\" 9.00` on your first sale 💰"
                    ),
                    color=0x00f5a0, timestamp=datetime.utcnow()
                ))

                bot.active_ventures.append({
                    'niche':    niche,
                    'research': research,
                    'listing':  listing,
                    'plan':     plan,
                    'started':  datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"Build pipeline error: {e}")
            if channel:
                await channel.send(f"❌ Pipeline error: {e}")

        await asyncio.sleep(15)
