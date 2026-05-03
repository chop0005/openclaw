"""
OpenClaw — Email & Newsletter Manager
Builds an owned audience via Beehiiv newsletter.
Every product gets a lead magnet → email capture → nurture sequence.

Revenue streams this unlocks:
- Sponsorships: $50-500/issue at 1k+ subscribers
- Paid newsletter tier: $5-10/mo
- Affiliate promotions to warm audience
- Product launches to existing buyers

Setup:
1. Create free account at beehiiv.com
2. Create a publication for your niche
3. Get API key from beehiiv.com/settings/api
4. Add BEEHIIV_API_KEY + BEEHIIV_PUBLICATION_ID to Railway
"""

import aiohttp
import asyncio
import logging
import discord
from datetime import datetime
from utils.claude import think, think_json
from config.settings import settings

logger = logging.getLogger("openclaw.newsletter")

BEEHIIV_BASE = "https://api.beehiiv.com/v2"

SYSTEM = """You are OpenClaw's Newsletter Content Specialist.
You write email newsletters that people actually want to read.
Your content is practical, specific, and personality-driven.
Always respond with valid JSON only."""


class BeehiivClient:
    def __init__(self):
        self.api_key = settings.BEEHIIV_API_KEY or ""
        self.pub_id  = settings.BEEHIIV_PUBLICATION_ID or ""

    def is_configured(self) -> bool:
        return bool(self.api_key and self.pub_id)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

    async def add_subscriber(self, email: str, name: str = "") -> dict:
        """Adds a subscriber to the newsletter."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "email":              email,
                "reactivate_existing": True,
                "send_welcome_email":  True,
                "utm_source":         "openclaw",
                "utm_medium":         "digital_product",
            }
            if name:
                payload["custom_fields"] = [{"name": "name", "value": name}]

            async with session.post(
                f"{BEEHIIV_BASE}/publications/{self.pub_id}/subscriptions",
                headers=self._headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                return {"success": resp.status in (200, 201), "data": data}

    async def get_subscriber_count(self) -> int:
        """Gets total subscriber count."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BEEHIIV_BASE}/publications/{self.pub_id}",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                return data.get("data", {}).get("stats", {}).get("total_subscribers", 0)

    async def create_post(self, post_data: dict) -> dict:
        """Creates a newsletter post (draft)."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "subject":        post_data.get("subject", ""),
                "subtitle":       post_data.get("subtitle", ""),
                "content":        post_data.get("content", ""),
                "status":         "draft",
                "platform":       "web",
                "audience":       "free",
            }
            async with session.post(
                f"{BEEHIIV_BASE}/publications/{self.pub_id}/posts",
                headers=self._headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                return {"success": resp.status in (200, 201), "data": data}


async def generate_lead_magnet(niche: str, product_name: str) -> dict:
    """
    Generates a lead magnet concept to capture emails with every product.
    The lead magnet is a free bonus that incentivizes email signup.
    """
    import json
    prompt = f"""Create a compelling lead magnet for this digital product niche:

Niche: {niche}
Product: {product_name}

The lead magnet should:
- Be a free bonus buyers get for joining the newsletter
- Take OpenClaw 5 minutes to create
- Be genuinely valuable (not fluff)
- Feel like a no-brainer to download

Return JSON:
{{
  "lead_magnet_name": "Name of the freebie",
  "lead_magnet_type": "PDF checklist | Mini template | Swipe file | Resource list | Email course",
  "value_proposition": "Why someone would give their email for this",
  "headline": "The headline for the signup form",
  "description": "2-3 sentence description of what they get",
  "content_outline": ["Page/section 1", "Page/section 2", "Page/section 3"],
  "cta_text": "Button text (e.g. 'Get Free Access' or 'Download Now')",
  "delivery_method": "Instant PDF download | 5-day email course | Notion template link",
  "estimated_conversion_rate": "e.g. 15-25% of visitors"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=1000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {
            "lead_magnet_name": f"Free {niche} Starter Kit",
            "lead_magnet_type": "PDF checklist",
            "value_proposition": "Get started immediately with this free resource",
            "headline": f"Get Your Free {niche} Starter Kit",
            "description": f"The essential checklist every {niche} enthusiast needs.",
            "cta_text": "Download Free",
            "delivery_method": "Instant PDF download",
            "estimated_conversion_rate": "15-20%"
        }


async def generate_newsletter_issue(niche: str, issue_number: int,
                                     recent_products: list, subscriber_count: int) -> dict:
    """Generates a complete newsletter issue."""
    import json
    prompt = f"""Write a complete newsletter issue for a {niche} digital product business.

Issue number: {issue_number}
Subscriber count: {subscriber_count}
Recent products: {json.dumps(recent_products[:3])}

Write in a friendly, knowledgeable tone — like a helpful expert friend.
Include practical value, not just promotion.

Return JSON:
{{
  "subject": "Email subject line (curiosity-driven, max 60 chars)",
  "subtitle": "Preview text (max 90 chars)",
  "sections": [
    {{
      "title": "Section title",
      "type": "tip | story | product | resource | ask",
      "content": "Full section content (2-4 paragraphs)",
      "cta": "Optional call to action"
    }}
  ],
  "ps_line": "P.S. line — usually drives most clicks",
  "sponsor_slot": "What type of sponsor would fit this audience",
  "estimated_open_rate": "e.g. 35-45% for engaged list",
  "monetization_note": "How this issue earns money"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=3000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {}


def newsletter_embed(issue: dict, niche: str) -> discord.Embed:
    """Discord embed showing newsletter issue preview."""
    embed = discord.Embed(
        title=f"📧 Newsletter Issue: {issue.get('subject', 'New Issue')[:80]}",
        description=issue.get("subtitle", ""),
        color=0x00c8f0,
        timestamp=datetime.utcnow()
    )

    sections = issue.get("sections", [])
    for s in sections[:3]:
        content_preview = s.get("content", "")[:300]
        embed.add_field(
            name=s.get("title", "Section"),
            value=content_preview + ("..." if len(s.get("content","")) > 300 else ""),
            inline=False
        )

    if issue.get("ps_line"):
        embed.add_field(name="P.S.", value=issue["ps_line"][:1024], inline=False)
    if issue.get("sponsor_slot"):
        embed.add_field(name="💼 Sponsor Fit", value=issue["sponsor_slot"][:1024], inline=True)
    if issue.get("estimated_open_rate"):
        embed.add_field(name="📊 Est. Open Rate", value=issue["estimated_open_rate"], inline=True)
    if issue.get("monetization_note"):
        embed.add_field(name="💰 Monetization", value=issue["monetization_note"][:1024], inline=False)

    embed.set_footer(text="OpenClaw Newsletter Engine • Review and send from Beehiiv dashboard")
    return embed


def lead_magnet_embed(lead_magnet: dict, niche: str) -> discord.Embed:
    """Shows the lead magnet concept."""
    embed = discord.Embed(
        title=f"🧲 Lead Magnet: {lead_magnet.get('lead_magnet_name', 'Freebie')[:80]}",
        description=lead_magnet.get("value_proposition", ""),
        color=0x00f5a0,
        timestamp=datetime.utcnow()
    )

    if lead_magnet.get("headline"):
        embed.add_field(name="📢 Signup Headline", value=lead_magnet["headline"][:1024], inline=False)
    if lead_magnet.get("description"):
        embed.add_field(name="📝 Description", value=lead_magnet["description"][:1024], inline=False)
    if lead_magnet.get("lead_magnet_type"):
        embed.add_field(name="Type", value=lead_magnet["lead_magnet_type"], inline=True)
    if lead_magnet.get("cta_text"):
        embed.add_field(name="Button Text", value=lead_magnet["cta_text"], inline=True)
    if lead_magnet.get("estimated_conversion_rate"):
        embed.add_field(name="Est. Conversion", value=lead_magnet["estimated_conversion_rate"], inline=True)

    outline = lead_magnet.get("content_outline", [])
    if outline:
        embed.add_field(
            name="📋 Content Outline",
            value="\n".join([f"• {item}" for item in outline[:5]]),
            inline=False
        )

    embed.set_footer(text="Add this freebie to your Etsy listing description to capture emails")
    return embed


async def run_newsletter_agent(bot, channel_id: int):
    """
    Monitors active ventures and generates lead magnets + newsletter issues.
    """
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        logger.error(f"Newsletter channel {channel_id} not found")
        return

    logger.info("Newsletter agent running")
    processed = set()

    while not bot.is_closed():
        try:
            beehiiv = BeehiivClient()
            ventures = getattr(bot, 'active_ventures', [])

            for venture in ventures:
                niche = venture.get('niche', '')
                research = venture.get('research', {})
                product_name = research.get('product_name', niche)

                if niche and niche not in processed and venture.get('listing'):
                    processed.add(niche)

                    # Generate lead magnet
                    await channel.send(embed=discord.Embed(
                        description=f"🧲 Generating lead magnet for **{niche}**...",
                        color=0x1e3d52
                    ))

                    lm = await generate_lead_magnet(niche, product_name)
                    if lm:
                        await channel.send(embed=lead_magnet_embed(lm, niche))

                    # Generate first newsletter issue
                    if beehiiv.is_configured():
                        sub_count = await beehiiv.get_subscriber_count()
                        products = [{'name': product_name, 'niche': niche}]
                        issue = await generate_newsletter_issue(niche, 1, products, sub_count)
                        if issue:
                            await channel.send(embed=newsletter_embed(issue, niche))

                            # Create draft in Beehiiv
                            content = "\n\n".join([
                                f"**{s.get('title','')}\n\n{s.get('content','')}"
                                for s in issue.get('sections', [])
                            ])
                            draft = await beehiiv.create_post({
                                "subject":  issue.get("subject", ""),
                                "subtitle": issue.get("subtitle", ""),
                                "content":  content,
                            })
                            if draft["success"]:
                                await channel.send(
                                    f"✅ Newsletter draft created in Beehiiv!\n"
                                    f"Review and send at beehiiv.com"
                                )

        except Exception as e:
            logger.error(f"Newsletter agent error: {e}")

        # Check weekly for new issues
        await asyncio.sleep(7 * 24 * 60 * 60)


NEWSLETTER_SETUP = """**📧 Newsletter Setup — 10 Minutes**

1. Go to **beehiiv.com** → Create free publication
2. Name it something related to your niche (e.g. "The Founder's Toolkit")
3. Go to Settings → API → Generate API key
4. Copy your Publication ID from the URL (beehiiv.com/settings — look for pub_xxx)

In Railway → Variables → add:
`BEEHIIV_API_KEY`          = your API key
`BEEHIIV_PUBLICATION_ID`   = your pub_xxx ID

OpenClaw will:
• Generate a lead magnet for each product (drives email signups)
• Write and draft newsletter issues weekly (you review + send)
• Track subscriber count in revenue dashboard

**Revenue unlock:** At 1,000 subscribers you can charge $50-200/issue for sponsorships."""
