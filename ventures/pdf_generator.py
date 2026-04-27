"""
OpenClaw — PDF Generator
Creates real, sellable PDF products (planners, workbooks, checklists)
from Claude-generated content using ReportLab.
Output is a downloadable file ready to upload to Etsy/Gumroad.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from utils.claude import think_json, think

logger = logging.getLogger("openclaw.pdf_generator")

# Try importing reportlab — graceful fallback if not installed yet
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not installed — PDF generation disabled. Run: pip install reportlab")

OUTPUT_DIR = "/tmp/openclaw-products"

SYSTEM = """You are OpenClaw's PDF Content Specialist.
You create high-quality, actionable content for digital products.
Your content is specific, practical, and worth paying for.
Always respond with valid JSON only."""


# ── Content Generation ────────────────────────────────────────

async def generate_pdf_content(product_name: str, product_type: str,
                                niche: str, sections: list) -> dict:
    """
    Generates complete content for a PDF product.
    Returns structured content ready for PDF rendering.
    """
    prompt = f"""Create complete, detailed content for this digital product:

Product: {product_name}
Type: {product_type}
Niche: {niche}
Sections to include: {json.dumps(sections)}

Generate REAL, USABLE content — not placeholders.
Every section should be immediately actionable.

Return JSON:
{{
  "title": "{product_name}",
  "subtitle": "Compelling subtitle",
  "tagline": "One-line value proposition",
  "brand_color": "#hex (pick a color that fits the niche)",
  "accent_color": "#hex (complementary accent)",
  "intro_text": "2-3 paragraph introduction (welcoming, sets expectations)",
  "pages": [
    {{
      "page_title": "Section title",
      "page_type": "content | worksheet | checklist | tracker | planner",
      "content_blocks": [
        {{
          "type": "heading | paragraph | bullet_list | numbered_list | fillable_lines | table | quote | tip_box",
          "content": "The actual content text or list items",
          "items": ["item 1", "item 2"] 
        }}
      ]
    }}
  ],
  "back_cover_text": "Closing message + call to action",
  "total_pages": 15
}}

Make it genuinely useful. Think: what would make someone leave a 5-star review?"""

    raw = await think_json(SYSTEM, prompt, max_tokens=4000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"PDF content JSON error: {e}")
        return {}


# ── PDF Rendering ─────────────────────────────────────────────

def render_pdf(content: dict, output_path: str) -> str:
    """
    Renders a PDF from structured content using ReportLab.
    Returns the path to the generated PDF file.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("ReportLab not installed. Run: pip install reportlab Pillow")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Colors from content
    try:
        brand_color  = HexColor(content.get('brand_color', '#2D3748'))
        accent_color = HexColor(content.get('accent_color', '#68D391'))
    except Exception:
        brand_color  = HexColor('#2D3748')
        accent_color = HexColor('#68D391')

    light_bg = HexColor('#F7FAFC')
    mid_gray  = HexColor('#718096')
    dark_text = HexColor('#1A202C')

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=white,
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=white,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontSize=11,
        textColor=HexColor('#E2E8F0'),
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=brand_color,
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold',
        borderPad=4
    )
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=brand_color,
        spaceBefore=12,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        textColor=dark_text,
        spaceAfter=6,
        leading=16,
        fontName='Helvetica'
    )
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontSize=10,
        textColor=dark_text,
        spaceAfter=4,
        leftIndent=20,
        bulletIndent=8,
        leading=15,
        fontName='Helvetica'
    )
    tip_style = ParagraphStyle(
        'Tip',
        parent=styles['Normal'],
        fontSize=10,
        textColor=dark_text,
        spaceAfter=6,
        leftIndent=12,
        rightIndent=12,
        leading=15,
        fontName='Helvetica-Oblique'
    )
    quote_style = ParagraphStyle(
        'Quote',
        parent=styles['Normal'],
        fontSize=13,
        textColor=brand_color,
        spaceAfter=8,
        leftIndent=20,
        rightIndent=20,
        alignment=TA_CENTER,
        leading=18,
        fontName='Helvetica-BoldOblique'
    )

    story = []

    # ── Cover Page ────────────────────────────────────────────
    cover_data = [[
        Paragraph(content.get('title', 'Untitled'), title_style),
        Paragraph(content.get('subtitle', ''), subtitle_style),
        Paragraph(content.get('tagline', ''), tagline_style),
    ]]
    cover_table = Table(cover_data, colWidths=[6.5 * inch])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), brand_color),
        ('ROWPADDING', (0, 0), (-1, -1), 24),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [8]),
    ]))
    story.append(Spacer(1, 1.5 * inch))
    story.append(cover_table)
    story.append(Spacer(1, 0.4 * inch))

    # Date + branding
    story.append(Paragraph(
        f"<font color='#{mid_gray.hexval()}'>Created {datetime.now().strftime('%B %Y')} • OpenClaw Digital Products</font>",
        ParagraphStyle('small', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)
    ))
    story.append(PageBreak())

    # ── Intro Page ────────────────────────────────────────────
    intro = content.get('intro_text', '')
    if intro:
        story.append(Paragraph("Welcome", h1_style))
        story.append(HRFlowable(width="100%", thickness=2, color=accent_color, spaceAfter=12))
        for para in intro.split('\n'):
            if para.strip():
                story.append(Paragraph(para.strip(), body_style))
        story.append(PageBreak())

    # ── Content Pages ─────────────────────────────────────────
    for page in content.get('pages', []):
        page_title = page.get('page_title', '')
        page_type  = page.get('page_type', 'content')

        if page_title:
            story.append(Paragraph(page_title, h1_style))
            story.append(HRFlowable(width="100%", thickness=2, color=accent_color, spaceAfter=10))

        for block in page.get('content_blocks', []):
            btype   = block.get('type', 'paragraph')
            bcontent = block.get('content', '')
            items   = block.get('items', [])

            if btype == 'heading':
                story.append(Paragraph(bcontent, h2_style))

            elif btype == 'paragraph':
                if bcontent:
                    story.append(Paragraph(bcontent, body_style))

            elif btype == 'bullet_list':
                all_items = items or (bcontent.split('\n') if bcontent else [])
                for item in all_items:
                    if item.strip():
                        story.append(Paragraph(f"• {item.strip()}", bullet_style))

            elif btype == 'numbered_list':
                all_items = items or (bcontent.split('\n') if bcontent else [])
                for i, item in enumerate(all_items, 1):
                    if item.strip():
                        story.append(Paragraph(f"{i}. {item.strip()}", bullet_style))

            elif btype == 'checklist':
                all_items = items or (bcontent.split('\n') if bcontent else [])
                for item in all_items:
                    if item.strip():
                        story.append(Paragraph(f"☐  {item.strip()}", bullet_style))

            elif btype == 'fillable_lines':
                label = bcontent or "Notes"
                story.append(Paragraph(label, h2_style))
                for _ in range(8):
                    story.append(HRFlowable(
                        width="100%", thickness=0.5,
                        color=HexColor('#CBD5E0'),
                        spaceAfter=18
                    ))

            elif btype == 'tracker':
                # Simple weekly tracker table
                headers = items if items else ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                table_data = [headers] + [[''] * len(headers)] * 4
                t = Table(table_data, colWidths=[6.5 * inch / len(headers)] * len(headers))
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), brand_color),
                    ('TEXTCOLOR', (0, 0), (-1, 0), white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E0')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, light_bg]),
                    ('ROWPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.2 * inch))

            elif btype == 'table':
                if items and len(items) > 0:
                    # items is list of rows, each row is a list
                    if isinstance(items[0], list):
                        table_data = items
                    else:
                        # Single column
                        table_data = [[item] for item in items]
                    t = Table(table_data)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), brand_color),
                        ('TEXTCOLOR', (0, 0), (-1, 0), white),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E0')),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, light_bg]),
                        ('ROWPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    story.append(t)

            elif btype == 'quote':
                story.append(Spacer(1, 0.1 * inch))
                story.append(Paragraph(f'"{bcontent}"', quote_style))
                story.append(Spacer(1, 0.1 * inch))

            elif btype == 'tip_box':
                tip_data = [[Paragraph(f"💡 {bcontent}", tip_style)]]
                tip_table = Table(tip_data, colWidths=[6.5 * inch])
                tip_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), light_bg),
                    ('ROUNDEDCORNERS', [6]),
                    ('ROWPADDING', (0, 0), (-1, -1), 10),
                    ('LEFTPADDING', (0, 0), (-1, -1), 14),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 14),
                ]))
                story.append(tip_table)
                story.append(Spacer(1, 0.1 * inch))

            story.append(Spacer(1, 0.05 * inch))

        story.append(PageBreak())

    # ── Back Cover ────────────────────────────────────────────
    back_text = content.get('back_cover_text', 'Thank you for your purchase!')
    back_data = [[Paragraph(back_text, subtitle_style)]]
    back_table = Table(back_data, colWidths=[6.5 * inch])
    back_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), brand_color),
        ('ROWPADDING', (0, 0), (-1, -1), 30),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(Spacer(1, 2 * inch))
    story.append(back_table)

    # Build PDF
    doc.build(story)
    logger.info(f"PDF generated: {output_path}")
    return output_path


# ── Main Entry Point ──────────────────────────────────────────

async def generate_pdf_product(product_name: str, niche: str,
                                sections: list, output_dir: str = OUTPUT_DIR) -> dict:
    """
    Full pipeline: generate content → render PDF → return result.
    Returns dict with file path and metadata.
    """
    logger.info(f"Generating PDF: {product_name}")

    content = await generate_pdf_content(product_name, "PDF Workbook/Planner", niche, sections)
    if not content:
        return {"success": False, "error": "Content generation failed"}

    safe_name = product_name.lower().replace(' ', '-').replace('/', '-')[:50]
    timestamp  = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(output_dir, f"{safe_name}_{timestamp}.pdf")

    try:
        path = render_pdf(content, output_path)
        size_kb = os.path.getsize(path) // 1024

        return {
            "success":      True,
            "path":         path,
            "filename":     os.path.basename(path),
            "size_kb":      size_kb,
            "product_name": product_name,
            "page_count":   len(content.get('pages', [])) + 3,
            "brand_color":  content.get('brand_color', '#2D3748'),
            "content":      content
        }
    except Exception as e:
        logger.error(f"PDF render error: {e}")
        return {"success": False, "error": str(e)}
