"""
OpenClaw — Venture Type Engine
Each venture type is a self-contained module with its own
build pipeline, launch sequence, and revenue model.
OpenClaw picks the best type for each opportunity automatically.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class VentureSpec:
    """A complete venture specification — the output of opportunity research."""
    id: str
    type: str                    # digital_product | micro_saas | chrome_extension | ai_tool | newsletter
    name: str
    tagline: str
    niche: str
    problem: str
    target_customer: str
    build_cost: float            # actual $ cost to build
    time_to_first_sale: str      # e.g. "7-14 days"
    revenue_model: str           # e.g. "Per sale $5-15"
    monthly_revenue_potential: str
    competition_level: str       # low | medium | high
    confidence_score: int        # 0-100
    platforms: list[str]         # where it sells (Etsy, Gumroad, etc.)
    build_steps: list[str]       # ordered list of what to actually do
    first_product_idea: str      # the specific first thing to make
    seo_keywords: list[str]      # top search terms buyers use
    price_point: str             # what to charge
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    approved: bool = False
    built: bool = False
    launched: bool = False
    revenue_earned: float = 0.0


@dataclass
class VentureType:
    """Base definition for a venture type."""
    key: str
    name: str
    description: str
    min_build_cost: float
    max_build_cost: float
    fastest_revenue_days: int    # realistic minimum days to first $
    revenue_ceiling: str         # e.g. "$500-5k/mo"
    platforms: list[str]
    requires_code: bool
    automation_level: str        # full | high | medium


# ── Venture Type Registry ─────────────────────────────────────────────────────
# Ordered by speed to first dollar + low capital requirement

VENTURE_TYPES = {

    "digital_product": VentureType(
        key="digital_product",
        name="Digital Product Store",
        description="Sell Notion templates, Canva designs, spreadsheets, planners on Etsy + Gumroad. Zero inventory, instant delivery, passive income.",
        min_build_cost=0.0,
        max_build_cost=20.0,
        fastest_revenue_days=7,
        revenue_ceiling="$500-8k/mo",
        platforms=["Etsy", "Gumroad", "Payhip"],
        requires_code=False,
        automation_level="full"
    ),

    "ai_tool": VentureType(
        key="ai_tool",
        name="AI Micro-Tool",
        description="Single-purpose AI-powered web tool (resume rewriter, cold email generator, ad copy tool). Free tier drives signups, paid tier converts.",
        min_build_cost=0.0,
        max_build_cost=30.0,
        fastest_revenue_days=14,
        revenue_ceiling="$300-5k/mo",
        platforms=["Vercel", "Product Hunt", "Gumroad"],
        requires_code=True,
        automation_level="high"
    ),

    "chrome_extension": VentureType(
        key="chrome_extension",
        name="Chrome Extension",
        description="Browser productivity tool sold on Chrome Web Store. One-time purchase or freemium. Low competition, global reach.",
        min_build_cost=5.0,
        max_build_cost=30.0,
        fastest_revenue_days=14,
        revenue_ceiling="$200-3k/mo",
        platforms=["Chrome Web Store", "Product Hunt"],
        requires_code=True,
        automation_level="high"
    ),

    "micro_saas": VentureType(
        key="micro_saas",
        name="Micro-SaaS",
        description="Small focused web app solving one problem with subscription revenue. Higher ceiling but longer build time.",
        min_build_cost=0.0,
        max_build_cost=50.0,
        fastest_revenue_days=30,
        revenue_ceiling="$1k-20k/mo",
        platforms=["Vercel", "Stripe", "Product Hunt"],
        requires_code=True,
        automation_level="medium"
    ),

    "newsletter": VentureType(
        key="newsletter",
        name="Niche Newsletter",
        description="Weekly email newsletter monetized via sponsorships and paid tier. OpenClaw writes every issue. Builds owned audience.",
        min_build_cost=0.0,
        max_build_cost=10.0,
        fastest_revenue_days=45,
        revenue_ceiling="$500-10k/mo",
        platforms=["Beehiiv", "Substack"],
        requires_code=False,
        automation_level="high"
    ),
}


def get_venture_type(key: str) -> Optional[VentureType]:
    return VENTURE_TYPES.get(key)


def rank_by_capital_and_speed(budget: float, target_days: int) -> list[VentureType]:
    """
    Returns venture types ranked by best fit for given budget and timeline.
    Used by the opportunity scanner to prioritize what to build first.
    """
    eligible = [v for v in VENTURE_TYPES.values() if v.min_build_cost <= budget]
    
    # Score by: speed to revenue (40%) + low cost (40%) + automation (20%)
    def score(v: VentureType) -> float:
        speed_score = max(0, 100 - (v.fastest_revenue_days / target_days * 100))
        cost_score = 100 - (v.min_build_cost / max(budget, 1) * 100)
        auto_score = {"full": 100, "high": 75, "medium": 50}.get(v.automation_level, 0)
        return (speed_score * 0.4) + (cost_score * 0.4) + (auto_score * 0.2)

    return sorted(eligible, key=score, reverse=True)
