"""
OpenClaw — Product Generator
Decides whether to build a PDF or Notion template based on the niche,
then generates the complete product and returns it ready for Etsy listing.
"""

import json
import logging
from utils.claude import think_json
from ventures.pdf_generator import generate_pdf_product
from ventures.notion_generator import generate_notion_template, generate_notion_build_guide, notion_spec_summary

logger = logging.getLogger("openclaw.product_generator")

SYSTEM = """You are OpenClaw's Product Strategist.
You decide what type of digital product will sell best for a given niche.
Always respond with valid JSON only."""

# Niches that work better as PDFs
PDF_NICHES = [
    "workbook", "planner", "journal", "checklist", "guide", "worksheet",
    "tracker", "budget", "finance", "habit", "goal", "meal", "fitness",
    "wellness", "recovery", "mental health", "burnout", "self-care",
    "gratitude", "affirmation", "coloring", "activity"
]

# Niches that work better as Notion templates
NOTION_NICHES = [
    "business", "productivity", "project", "crm", "client", "freelance",
    "content", "social media", "marketing", "saas", "startup", "founder",
    "student", "study", "research", "reading", "knowledge", "second brain",
    "pkm", "dashboard", "kanban", "database", "system", "workflow"
]


def decide_product_type(niche: str, product_name: str) -> str:
    """
    Decides PDF or Notion based on niche keywords.
    Returns 'pdf' or 'notion'.
    """
    combined = (niche + " " + product_name).lower()

    pdf_score    = sum(1 for k in PDF_NICHES    if k in combined)
    notion_score = sum(1 for k in NOTION_NICHES if k in combined)

    if pdf_score > notion_score:
        return "pdf"
    elif notion_score > pdf_score:
        return "notion"
    else:
        # Default: PDFs are easier to sell and require no setup from buyer
        return "pdf"


async def get_product_structure(product_name: str, niche: str,
                                 product_type: str, research: dict) -> dict:
    """
    Generates the specific structure/sections for the product.
    """
    prompt = f"""Design the optimal structure for this digital product:

Product: {product_name}
Type: {product_type.upper()} ({'PDF planner/workbook' if product_type == 'pdf' else 'Notion template'})
Niche: {niche}
Buyer: {research.get('buyer_persona', 'general user')}
Pain point: {research.get('pain_point', '')}
What to include: {json.dumps(research.get('what_to_include', []))}

Return JSON:
{{
  "sections": ["Section 1", "Section 2", "Section 3", "Section 4", "Section 5", "Section 6"],
  "use_case": "One sentence describing the primary use case",
  "unique_angle": "What makes this different from generic templates",
  "page_count_estimate": 15,
  "complexity": "simple | moderate | comprehensive"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=1000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {
            "sections": research.get('what_to_include', ['Introduction', 'Main Content', 'Worksheets', 'Action Plan', 'Resources']),
            "use_case": f"Help {research.get('buyer_persona', 'users')} with {niche}",
            "unique_angle": "Practical and immediately usable",
            "page_count_estimate": 15,
            "complexity": "moderate"
        }


async def generate_product(research: dict, niche: str) -> dict:
    """
    Main entry point. Takes research data, generates the full product.

    Returns:
    {
        "type": "pdf" | "notion",
        "product_name": str,
        "niche": str,
        "result": { ...type-specific data... },
        "summary": str,           # Discord-friendly summary
        "ready_to_list": bool
    }
    """
    product_name = research.get('product_name', f'{niche} Template')
    logger.info(f"Generating product: {product_name}")

    # Step 1: Decide type
    product_type = decide_product_type(niche, product_name)
    logger.info(f"Product type decision: {product_type.upper()} for '{product_name}'")

    # Step 2: Get structure
    structure = await get_product_structure(product_name, niche, product_type, research)
    sections  = structure.get('sections', [])

    # Step 3: Generate product
    if product_type == "pdf":
        result = await generate_pdf_product(product_name, niche, sections)
        if result.get('success'):
            summary = (
                f"**📄 PDF Generated: {product_name}**\n"
                f"• Pages: ~{result.get('page_count', 15)}\n"
                f"• File size: {result.get('size_kb', 0)} KB\n"
                f"• File: `{result.get('filename', 'product.pdf')}`\n"
                f"• Ready to upload to Etsy/Gumroad ✅"
            )
        else:
            summary = f"❌ PDF generation failed: {result.get('error', 'Unknown error')}"

    else:  # notion
        result = await generate_notion_template(
            product_name, niche,
            structure.get('use_case', ''),
            sections
        )
        if result:
            build_guide = await generate_notion_build_guide(result)
            result['build_guide'] = build_guide
            summary = notion_spec_summary(result)
            result['success'] = True
        else:
            result = {'success': False, 'error': 'Notion template generation failed'}
            summary = "❌ Notion template generation failed"

    return {
        "type":          product_type,
        "product_name":  product_name,
        "niche":         niche,
        "structure":     structure,
        "result":        result,
        "summary":       summary,
        "ready_to_list": result.get('success', False)
    }
