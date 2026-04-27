"""
OpenClaw — Notion Template Generator
Generates complete Notion template specs with full page structure.
Outputs a detailed build guide + shareable template description
that buyers duplicate into their own Notion workspace.
"""

import json
import logging
from utils.claude import think_json

logger = logging.getLogger("openclaw.notion_generator")

SYSTEM = """You are OpenClaw's Notion Template Specialist.
You design beautiful, functional Notion templates that people love to use.
You know Notion's features deeply: databases, views, relations, formulas, callout blocks.
You create templates that are immediately usable, not empty shells.
Always respond with valid JSON only."""


async def generate_notion_template(product_name: str, niche: str,
                                    use_case: str, sections: list) -> dict:
    """
    Generates a complete Notion template specification.
    Returns full build instructions + product description.
    """
    prompt = f"""Design a complete Notion template for:

Product: {product_name}
Niche: {niche}
Use Case: {use_case}
Key Sections: {json.dumps(sections)}

Create a template that's genuinely impressive and immediately useful.
Use Notion's best features: databases with views, kanban boards, progress tracking,
linked databases, formulas where useful, callout blocks for tips.

Return JSON:
{{
  "template_name": "{product_name}",
  "tagline": "Compelling one-line description",
  "notion_emoji": "Single emoji that represents this template",
  "cover_color": "light_gray | light_brown | light_orange | light_yellow | light_teal | light_blue | light_pink | light_purple | light_red",
  "template_overview": "3-4 sentence description of what the buyer gets",
  "pages": [
    {{
      "page_name": "Page name with emoji",
      "page_type": "page | database | board | calendar | gallery | list | timeline",
      "icon": "emoji",
      "description": "What this page does",
      "properties": [
        {{
          "name": "Property name",
          "type": "text | number | select | multi_select | date | checkbox | url | email | formula | relation | rollup | people | files",
          "options": ["option1", "option2"]
        }}
      ],
      "views": ["Table view", "Board view", "Calendar view"],
      "sample_entries": [
        {{"name": "Example row 1", "details": "Sample data"}},
        {{"name": "Example row 2", "details": "Sample data"}}
      ],
      "callout_blocks": [
        {{"emoji": "💡", "text": "Helpful tip for using this page"}}
      ]
    }}
  ],
  "setup_steps": [
    "Step 1: Duplicate this template to your Notion workspace",
    "Step 2: ...",
    "Step 3: ..."
  ],
  "key_features": ["Feature 1", "Feature 2", "Feature 3", "Feature 4", "Feature 5"],
  "who_its_for": "Specific description of ideal user",
  "time_to_set_up": "e.g. 5 minutes",
  "compatibility": "Notion Free, Plus, Business, and Enterprise",
  "build_instructions": [
    {{
      "step": 1,
      "action": "Create the first page",
      "details": "Detailed instructions for building this in Notion"
    }}
  ],
  "etsy_preview_description": "What to write in the Etsy listing preview showing template features",
  "duplicate_link_placeholder": "https://notion.so/templates/YOUR-LINK-HERE"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=4000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"Notion template JSON error: {e}")
        return {}


async def generate_notion_build_guide(template: dict) -> str:
    """
    Generates a step-by-step guide for actually building the template in Notion.
    This is what OpenClaw posts to Discord so you can build it yourself.
    """
    pages_summary = "\n".join([
        f"- {p.get('page_name')}: {p.get('description', '')}"
        for p in template.get('pages', [])
    ])

    prompt = f"""Write a clear, step-by-step guide for building this Notion template:

Template: {template.get('template_name')}
Pages to create:
{pages_summary}

Write it as numbered steps a beginner can follow.
Include: what to name each page, what database properties to add,
what views to create, what sample content to add.
Be specific — mention exact Notion features to use.
Max 800 words."""

    from utils.claude import think
    return await think(SYSTEM, prompt, max_tokens=1500)


def notion_spec_summary(template: dict) -> str:
    """Returns a Discord-friendly summary of the template spec."""
    pages = template.get('pages', [])
    features = template.get('key_features', [])

    lines = [
        f"**{template.get('template_name')}**",
        f"*{template.get('tagline', '')}*",
        "",
        f"**Pages ({len(pages)}):**",
    ]
    for p in pages:
        lines.append(f"• {p.get('page_name')} — {p.get('description', '')[:80]}")

    if features:
        lines.append("")
        lines.append("**Key Features:**")
        for f in features[:4]:
            lines.append(f"• {f}")

    lines += [
        "",
        f"**Setup time:** {template.get('time_to_set_up', '5 min')}",
        f"**Who it's for:** {template.get('who_its_for', '')}",
    ]

    return "\n".join(lines)
