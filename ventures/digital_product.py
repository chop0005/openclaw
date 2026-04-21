"""
OpenClaw — Digital Product Venture
The fastest path to $500. Claude generates ready-to-sell
Notion templates, Canva designs, spreadsheets, and planners.
Lists them on Etsy + Gumroad with full SEO optimization.
"""

import json
import logging
from utils.claude import think_json, think
from ventures.base import VentureSpec

logger = logging.getLogger("openclaw.ventures.digital_product")

SYSTEM = """You are OpenClaw's Digital Product Specialist — an expert at creating
and selling digital templates on Etsy and Gumroad.

You know exactly what sells: Notion templates, Canva designs, Google Sheets trackers,
planners, swipe files, checklists, and productivity systems.

You understand Etsy SEO deeply — title structure, tag optimization, pricing psychology.
You know that $7-15 is the sweet spot for impulse buys.
You know that "aesthetic," "minimalist," and "2025" convert well in titles.

Always respond with valid JSON only. No markdown. No explanation."""


async def research_opportunity(niche: str, budget: float) -> dict:
    """
    Researches a specific niche and returns a complete digital product opportunity.
    """
    prompt = f"""Research a digital product opportunity in this niche: {niche}
Budget available: ${budget}

Find a SPECIFIC gap in the Etsy/Gumroad marketplace right now.
Think about what people search for but can't find a great version of.

Return a JSON object:
{{
  "product_name": "Specific product name (what you'd call it on Etsy)",
  "product_type": "Notion Template | Canva Template | Google Sheets | PDF Planner | Swipe File",
  "niche": "Specific niche (e.g. 'freelance invoice tracking' not just 'business')",
  "search_volume": "High | Medium | Low — based on Etsy search behavior",
  "competition": "Low | Medium | High",
  "price_point": "$7 | $9 | $12 | $15 | $19",
  "buyer_persona": "Who buys this and why (1 sentence)",
  "pain_point": "The specific problem this solves",
  "etsy_title": "Full optimized Etsy title (140 chars, keyword-rich)",
  "etsy_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10", "tag11", "tag12", "tag13"],
  "etsy_description": "Full Etsy listing description (300-400 words, SEO optimized, conversational)",
  "gumroad_pitch": "Short Gumroad product description (100 words)",
  "what_to_include": ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"],
  "upsell_opportunity": "What you could sell them next",
  "monthly_potential": "Realistic monthly revenue if 2-3 sales/day",
  "confidence_score": 85
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=2500)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"Research JSON error: {e}")
        return {}


async def generate_product_content(product: dict) -> dict:
    """
    Generates the actual content/structure of the digital product.
    Returns a detailed spec a human (or AI) can use to build it.
    """
    prompt = f"""Create the complete content specification for this digital product:

Product: {product.get('product_name')}
Type: {product.get('product_type')}
What to include: {json.dumps(product.get('what_to_include', []))}
Buyer: {product.get('buyer_persona')}
Pain point: {product.get('pain_point')}

Generate the COMPLETE content — every section, page, tab, or component.
Be specific enough that someone could build this in Notion, Canva, or Google Sheets
by following your spec exactly.

Return JSON:
{{
  "product_name": "{product.get('product_name')}",
  "format": "Notion | Canva | Google Sheets | PDF",
  "sections": [
    {{
      "name": "Section name",
      "purpose": "What it does for the buyer",
      "content": "Detailed description of what goes here",
      "example_items": ["Example 1", "Example 2", "Example 3"]
    }}
  ],
  "design_direction": "Visual style description (colors, fonts, vibe)",
  "bonus_items": ["Bonus 1", "Bonus 2"],
  "setup_instructions": ["Step 1", "Step 2", "Step 3"],
  "build_time_estimate": "e.g. 2-3 hours in Notion",
  "tools_needed": ["Notion free tier", "Canva free", "etc"],
  "mockup_description": "What the preview/thumbnail should look like"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=3000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"Content spec JSON error: {e}")
        return {}


async def generate_listing_pack(product: dict, content: dict) -> dict:
    """
    Generates a complete ready-to-copy listing pack:
    Etsy title, description, tags, Gumroad copy, social teaser.
    """
    prompt = f"""Create a complete listing pack for this digital product:

Product: {product.get('product_name')}
Type: {product.get('product_type')}
Niche: {product.get('niche')}
Price: {product.get('price_point')}
Pain point solved: {product.get('pain_point')}
Buyer: {product.get('buyer_persona')}
Sections: {[s['name'] for s in content.get('sections', [])]}

Return JSON:
{{
  "etsy_title": "Full 140-char Etsy title — keyword rich, includes year if relevant",
  "etsy_tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10","tag11","tag12","tag13"],
  "etsy_description": "Full listing description — 400+ words. Start with a hook. Include what's inside, who it's for, how it works, what they get. Use line breaks. End with FAQ.",
  "etsy_price": "{product.get('price_point', '$9')}",
  "gumroad_name": "Product name for Gumroad",
  "gumroad_description": "Gumroad product description — punchy, 150 words, bullet points",
  "gumroad_price": "{product.get('price_point', '$9')}",
  "pinterest_caption": "Pinterest pin caption (150 chars)",
  "tiktok_hook": "First 3 seconds of a TikTok about this product",
  "instagram_caption": "Instagram caption with hashtags",
  "reddit_pitch": "How to mention this naturally in relevant subreddits"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=3000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"Listing pack JSON error: {e}")
        return {}


async def generate_product_batch(niche: str, count: int = 5) -> list[dict]:
    """
    Generates a batch of related products to build a full store.
    A store with 20-30 listings converts dramatically better than 1-2.
    """
    prompt = f"""Generate {count} related digital products for a store in this niche: {niche}

These should be complementary — a buyer of product 1 might also want products 2, 3, 4.
Vary the price points ($5, $7, $9, $12, $15).
Include at least one bundle idea.

Return a JSON array with {count} objects:
{{
  "name": "Product name",
  "type": "Notion | Canva | Sheets | PDF | Bundle",
  "price": "$9",
  "one_line_description": "What it does",
  "primary_keyword": "Main Etsy search term",
  "estimated_monthly_sales": "2-5 per month at launch"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=2000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(clean)
        return result if isinstance(result, list) else []
    except Exception as e:
        logger.error(f"Product batch JSON error: {e}")
        return []


async def generate_launch_strategy(niche: str, budget: float) -> dict:
    """
    Creates a day-by-day 30-day launch plan for hitting $500.
    """
    prompt = f"""Create a 30-day launch plan to reach $500 in revenue selling digital products in: {niche}
Available budget: ${budget}

Be realistic and specific. Account for:
- Etsy listing fees ($0.20/listing)
- Time to rank in Etsy search (2-3 weeks)
- Free promotion channels (Pinterest, TikTok, Reddit)
- Paid promotion timing (don't spend until organic works)

Return JSON:
{{
  "goal": "$500 in 30 days",
  "strategy_summary": "2-3 sentence overview",
  "week_1": {{
    "focus": "Main focus this week",
    "tasks": ["Task 1", "Task 2", "Task 3", "Task 4"],
    "listings_to_create": 10,
    "budget_spend": "$0-5",
    "expected_revenue": "$0-20"
  }},
  "week_2": {{
    "focus": "Main focus",
    "tasks": ["Task 1", "Task 2", "Task 3", "Task 4"],
    "listings_to_create": 10,
    "budget_spend": "$5-10",
    "expected_revenue": "$20-80"
  }},
  "week_3": {{
    "focus": "Main focus",
    "tasks": ["Task 1", "Task 2", "Task 3", "Task 4"],
    "listings_to_create": 5,
    "budget_spend": "$10-15",
    "expected_revenue": "$80-200"
  }},
  "week_4": {{
    "focus": "Main focus",
    "tasks": ["Task 1", "Task 2", "Task 3", "Task 4"],
    "listings_to_create": 5,
    "budget_spend": "$15-20",
    "expected_revenue": "$200-500"
  }},
  "free_traffic_channels": ["Channel 1 with tactic", "Channel 2 with tactic", "Channel 3 with tactic"],
  "paid_traffic_when": "When to start and what to spend",
  "bundle_strategy": "How to bundle products for higher AOV",
  "milestone_1": "First sale — what triggers this",
  "milestone_2": "$100 — what changed",
  "milestone_3": "$500 — what the store looks like at this point",
  "month_2_projection": "What's possible in month 2 with reinvestment"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=3000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"Launch strategy JSON error: {e}")
        return {}
