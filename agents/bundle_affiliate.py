"""
OpenClaw — Bundle Builder + Affiliate Revenue Layer

Bundle Builder:
Groups related products into bundles at 2-3x price.
Bundles convert better and increase average order value.

Affiliate Layer:
Automatically adds affiliate links to all content.
Passive income stacked on every post and listing.
Works with: Notion, Canva, ConvertKit, Gumroad affiliates.
"""

import asyncio
import json
import logging
import discord
from datetime import datetime
from utils.claude import think_json
from config.settings import settings

logger = logging.getLogger("openclaw.bundles_affiliates")

SYSTEM = """You are OpenClaw's Revenue Optimization Specialist.
You create bundles and affiliate strategies that maximize revenue per customer.
Always respond with valid JSON only."""


# ── Bundle Builder ────────────────────────────────────────────

async def create_bundle(products: list, niche: str) -> dict:
    """Creates a bundle offering from existing products."""
    prompt = f"""Create a compelling product bundle for this digital product store:

Niche: {niche}
Individual products: {json.dumps(products)}

Design a bundle that:
- Is priced at 2-2.5x the highest individual product
- Feels like a massive value deal
- Has a compelling name and angle
- Would convert buyers who are browsing

Return JSON:
{{
  "bundle_name": "Name of the bundle",
  "bundle_tagline": "Value proposition in one line",
  "included_products": ["Product 1", "Product 2", "Product 3"],
  "individual_total": "$X total if bought separately",
  "bundle_price": "$Y (recommended bundle price)",
  "savings_amount": "$Z savings",
  "savings_percent": "XX% off",
  "etsy_title": "Full Etsy listing title for the bundle",
  "etsy_description": "Bundle listing description (200 words)",
  "etsy_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
  "conversion_angle": "Why buyers will choose the bundle over individual items",
  "upsell_timing": "When to show this bundle (e.g. after first purchase)",
  "monthly_potential": "Expected monthly revenue from bundle sales"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=2000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {}


def bundle_embed(bundle: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"📦 Bundle: {bundle.get('bundle_name', 'New Bundle')[:80]}",
        description=bundle.get("bundle_tagline", ""),
        color=0x00f5a0,
        timestamp=datetime.utcnow()
    )

    included = bundle.get("included_products", [])
    if included:
        embed.add_field(
            name="📋 Included Products",
            value="\n".join([f"• {p}" for p in included]),
            inline=False
        )

    embed.add_field(
        name="💰 Pricing",
        value=(
            f"Individual: {bundle.get('individual_total','N/A')}\n"
            f"**Bundle: {bundle.get('bundle_price','N/A')}**\n"
            f"Savings: {bundle.get('savings_amount','N/A')} ({bundle.get('savings_percent','N/A')})"
        ),
        inline=True
    )

    if bundle.get("monthly_potential"):
        embed.add_field(
            name="📈 Potential",
            value=bundle["monthly_potential"],
            inline=True
        )

    if bundle.get("etsy_title"):
        embed.add_field(
            name="📝 Etsy Title",
            value=f"```{bundle['etsy_title'][:950]}```",
            inline=False
        )

    if bundle.get("etsy_tags"):
        embed.add_field(
            name="🏷️ Tags",
            value=", ".join(bundle["etsy_tags"][:13]),
            inline=False
        )

    embed.set_footer(text="OpenClaw Bundle Builder • List this as a separate Etsy product")
    return embed


# ── Affiliate Layer ───────────────────────────────────────────

# High-converting affiliate programs for digital product creators
AFFILIATE_PROGRAMS = {
    "notion": {
        "name": "Notion",
        "url": "https://affiliate.notion.so",
        "commission": "50% first year",
        "cookie": "90 days",
        "relevance": ["productivity", "templates", "notion", "workspace", "organization"],
        "cta": "Try Notion free →"
    },
    "canva": {
        "name": "Canva Pro",
        "url": "https://partner.canva.com",
        "commission": "$36 per Pro signup",
        "cookie": "30 days",
        "relevance": ["design", "canva", "templates", "graphics", "visual"],
        "cta": "Design for free with Canva →"
    },
    "convertkit": {
        "name": "ConvertKit",
        "url": "https://convertkit.com/referral",
        "commission": "30% recurring",
        "cookie": "90 days",
        "relevance": ["email", "newsletter", "creator", "audience", "marketing"],
        "cta": "Build your email list →"
    },
    "gumroad": {
        "name": "Gumroad",
        "url": "https://gumroad.com/affiliates",
        "commission": "10% of sales",
        "cookie": "30 days",
        "relevance": ["digital products", "selling", "creator", "downloads"],
        "cta": "Sell digital products →"
    },
    "beehiiv": {
        "name": "Beehiiv",
        "url": "https://www.beehiiv.com/partners",
        "commission": "50% first 12 months",
        "cookie": "60 days",
        "relevance": ["newsletter", "email", "creator", "audience", "subscribers"],
        "cta": "Start your newsletter →"
    },
    "creative_fabrica": {
        "name": "Creative Fabrica",
        "url": "https://www.creativefabrica.com/affiliates",
        "commission": "35% commission",
        "cookie": "30 days",
        "relevance": ["fonts", "graphics", "design", "templates", "crafts"],
        "cta": "Unlimited creative assets →"
    },
}


def get_relevant_affiliates(niche: str, content: str) -> list:
    """Returns affiliate programs relevant to niche and content."""
    combined = (niche + " " + content).lower()
    relevant = []

    for key, program in AFFILIATE_PROGRAMS.items():
        relevance_score = sum(
            1 for keyword in program["relevance"]
            if keyword in combined
        )
        if relevance_score > 0:
            relevant.append({**program, "key": key, "score": relevance_score})

    return sorted(relevant, key=lambda x: x["score"], reverse=True)[:3]


async def generate_affiliate_content(
    niche: str,
    platform: str,
    affiliate_program: dict
) -> dict:
    """Generates content with natural affiliate link integration."""

    prompt = f"""Create a social media post that naturally includes an affiliate recommendation:

Niche: {niche}
Platform: {platform}
Affiliate product: {affiliate_program.get('name')}
Commission: {affiliate_program.get('commission')}
CTA: {affiliate_program.get('cta')}

The affiliate mention must feel completely natural — like a genuine recommendation.
Not salesy. The product must be genuinely useful for this audience.

Return JSON:
{{
  "platform": "{platform}",
  "content": "Full post with natural affiliate mention",
  "affiliate_placement": "Where/how the affiliate link appears",
  "disclosure": "FTC disclosure text (short, natural)",
  "estimated_clicks": "Expected clicks per 1000 views",
  "estimated_monthly_revenue": "At your current following size"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=800)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {}


def affiliate_embed(programs: list, niche: str) -> discord.Embed:
    """Shows relevant affiliate programs for a niche."""
    embed = discord.Embed(
        title=f"💸 Affiliate Opportunities: {niche[:60]}",
        description="Revenue stacked on every piece of content. Set up once, earn forever.",
        color=0xffc944,
        timestamp=datetime.utcnow()
    )

    for prog in programs[:4]:
        embed.add_field(
            name=f"💰 {prog.get('name')}",
            value=(
                f"Commission: **{prog.get('commission')}**\n"
                f"Cookie: {prog.get('cookie')}\n"
                f"Sign up: {prog.get('url')}"
            ),
            inline=True
        )

    embed.add_field(
        name="📋 How to Use",
        value=(
            "1. Sign up for each program above\n"
            "2. Get your unique affiliate link\n"
            "3. Add to Railway: `AFFILIATE_NOTION`, `AFFILIATE_CANVA` etc.\n"
            "4. OpenClaw auto-includes links in all relevant content"
        ),
        inline=False
    )

    embed.set_footer(text="OpenClaw Affiliate Layer • Passive income on every post")
    return embed


# ── Main Runner ───────────────────────────────────────────────

async def run_bundle_and_affiliate_engine(bot, channel_id: int):
    """
    Monitors active ventures and:
    1. Creates bundles when 2+ products exist
    2. Identifies affiliate opportunities
    3. Posts both to the build pipeline channel
    """
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    logger.info("Bundle + Affiliate engine running")
    processed = set()

    while not bot.is_closed():
        try:
            ventures = getattr(bot, 'active_ventures', [])

            for venture in ventures:
                niche    = venture.get('niche', '')
                research = venture.get('research', {})

                if not niche or niche in processed:
                    continue

                processed.add(niche)

                # Get products for this venture
                products = [
                    research.get('product_name', niche),
                    f"{niche} Starter Kit",
                    f"Complete {niche} Bundle"
                ]

                # Create bundle
                bundle = await create_bundle(products, niche)
                if bundle:
                    await channel.send(embed=bundle_embed(bundle))

                # Find affiliate opportunities
                affiliates = get_relevant_affiliates(niche, niche)
                if affiliates:
                    await channel.send(embed=affiliate_embed(affiliates, niche))

        except Exception as e:
            logger.error(f"Bundle/affiliate engine error: {e}")

        await asyncio.sleep(24 * 60 * 60)  # Daily check
