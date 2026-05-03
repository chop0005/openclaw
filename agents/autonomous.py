"""
OpenClaw — Autonomous Mode Engine
Smart decision routing: small decisions auto-execute,
big decisions get surfaced to you for approval.

Decision categories:
  AUTO (no approval needed):
  - Trend scanning and research
  - Content generation
  - Social posting (approved platforms)
  - Analytics and reporting
  - Lead magnet creation
  - Price optimization suggestions

  APPROVE (needs your thumbs up):
  - New product builds (>$0 cost)
  - Listing on Etsy/Gumroad
  - Spending any budget
  - New niche pivots
  - Major strategy changes
  - Anything that touches money

The engine runs continuously, finds opportunities,
executes what it can, and surfaces approvals for the rest.
"""

import asyncio
import json
import logging
import discord
from datetime import datetime, timedelta
from utils.claude import think_json, think
from config.settings import settings

logger = logging.getLogger("openclaw.autonomous")

SYSTEM = """You are OpenClaw's Autonomous Decision Engine.
You analyze situations and decide what to do without being asked.
You are conservative with money and aggressive with free actions.
Always respond with valid JSON only."""


# ── Decision Classification ───────────────────────────────────

AUTO_DECISIONS = {
    "scan_trends",
    "generate_content",
    "post_social",
    "run_analytics",
    "update_seo",
    "generate_lead_magnet",
    "monitor_competitors",
    "send_newsletter_draft",
    "generate_product_batch",
    "research_niche",
}

APPROVE_DECISIONS = {
    "build_product",
    "list_on_etsy",
    "list_on_gumroad",
    "spend_budget",
    "pivot_niche",
    "launch_ads",
    "publish_newsletter",
    "change_pricing",
}


def needs_approval(decision_type: str) -> bool:
    """Returns True if this decision needs operator approval."""
    return decision_type in APPROVE_DECISIONS


async def evaluate_opportunity(opportunity: dict, revenue_log: dict, ventures: list) -> dict:
    """
    Evaluates an opportunity and decides what action to take.
    Returns a decision with reasoning.
    """
    total_revenue = sum(revenue_log.values()) if revenue_log else 0
    active_niches = [v.get('niche') for v in ventures if v.get('niche')]

    prompt = f"""Evaluate this opportunity and decide the best action:

Opportunity: {json.dumps(opportunity)}
Current revenue: ${total_revenue:.2f}
Active niches: {active_niches}
Capital budget: ${settings.CAPITAL_BUDGET}
Revenue target: ${settings.REVENUE_TARGET} in {settings.TARGET_DAYS} days

Decide what OpenClaw should do autonomously:

Return JSON:
{{
  "decision": "build_product | scan_trends | generate_content | skip | research_niche",
  "reasoning": "Why this decision",
  "confidence": 85,
  "urgency": "high | medium | low",
  "expected_impact": "What this will do for revenue",
  "requires_approval": true/false,
  "auto_action": "What to do immediately without approval",
  "approval_message": "What to ask operator if approval needed",
  "estimated_time": "Time to complete"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=1000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {
            "decision": "research_niche",
            "reasoning": "Default to safe research action",
            "confidence": 70,
            "requires_approval": False,
            "auto_action": "Run market analysis"
        }


async def generate_daily_plan(ventures: list, revenue_log: dict) -> dict:
    """
    Generates OpenClaw's autonomous action plan for the day.
    What it will do automatically vs what needs approval.
    """
    total = sum(revenue_log.values()) if revenue_log else 0
    active = [v.get('niche') for v in ventures if v.get('niche')]

    prompt = f"""Create OpenClaw's autonomous action plan for today:

Revenue so far: ${total:.2f} / ${settings.REVENUE_TARGET:.0f} target
Active ventures: {active or ['none yet']}
Capital available: ${settings.CAPITAL_BUDGET}
Days remaining: {settings.TARGET_DAYS}

What should OpenClaw do TODAY to maximize revenue?
Separate into: will do automatically vs needs approval.

Return JSON:
{{
  "date": "{datetime.now().strftime('%B %d, %Y')}",
  "revenue_status": "on track | behind | ahead",
  "auto_actions": [
    {{"action": "Action name", "reason": "Why", "timing": "When today"}}
  ],
  "approval_needed": [
    {{"action": "Action name", "reason": "Why", "impact": "Expected result", "cost": "$0"}}
  ],
  "priority_focus": "Single most important thing today",
  "revenue_projection": "Expected revenue if plan executes",
  "bottleneck": "Biggest thing slowing revenue right now"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=1500)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {}


def plan_embed(plan: dict) -> discord.Embed:
    """Discord embed for the daily autonomous plan."""

    status = plan.get("revenue_status", "unknown")
    colors = {"on track": 0x00f5a0, "ahead": 0x58a6ff, "behind": 0xff7733}
    color  = colors.get(status, 0x00c8f0)

    embed = discord.Embed(
        title=f"🤖 OpenClaw Daily Plan — {plan.get('date', datetime.now().strftime('%b %d'))}",
        description=(
            f"**Revenue Status:** {status.upper()}\n"
            f"**Priority:** {plan.get('priority_focus', 'N/A')}\n"
            f"**Bottleneck:** {plan.get('bottleneck', 'N/A')}"
        ),
        color=color,
        timestamp=datetime.utcnow()
    )

    auto_actions = plan.get("auto_actions", [])
    if auto_actions:
        auto_text = "\n".join([
            f"• {a.get('action')} — {a.get('timing', 'today')}"
            for a in auto_actions[:5]
        ])
        embed.add_field(
            name="⚡ Doing Automatically",
            value=auto_text[:1024],
            inline=False
        )

    approvals = plan.get("approval_needed", [])
    if approvals:
        approval_text = "\n".join([
            f"• {a.get('action')} → {a.get('impact', '')[:80]}"
            for a in approvals[:4]
        ])
        embed.add_field(
            name="✋ Needs Your Approval",
            value=approval_text[:1024],
            inline=False
        )

    if plan.get("revenue_projection"):
        embed.add_field(
            name="📈 Revenue Projection",
            value=plan["revenue_projection"][:512],
            inline=False
        )

    embed.set_footer(text="OpenClaw Autonomous Mode • Approve items above to unlock more automation")
    return embed


class ApprovalView(discord.ui.View):
    """Generic approval buttons for any autonomous action."""

    def __init__(self, action: dict, bot_ref):
        super().__init__(timeout=None)
        self.action  = action
        self.bot_ref = bot_ref

    @discord.ui.button(label="✅ Approve & Execute", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        action_name = self.action.get("action", "this action")
        await interaction.response.send_message(
            f"✅ **{action_name}** approved! OpenClaw is executing now.",
            ephemeral=False
        )
        # Add to approved queue
        if not hasattr(self.bot_ref, 'autonomous_queue'):
            self.bot_ref.autonomous_queue = []
        self.bot_ref.autonomous_queue.append({
            **self.action,
            "approved_at": datetime.now().isoformat(),
            "approved_by": str(interaction.user)
        })
        self.stop()

    @discord.ui.button(label="❌ Skip", style=discord.ButtonStyle.danger)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏭️ Skipped.", ephemeral=False)
        self.stop()

    @discord.ui.button(label="🔍 More Info", style=discord.ButtonStyle.secondary)
    async def more_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        detail = (
            f"**Action:** {self.action.get('action', 'N/A')}\n"
            f"**Reason:** {self.action.get('reason', 'N/A')}\n"
            f"**Impact:** {self.action.get('impact', 'N/A')}\n"
            f"**Cost:** {self.action.get('cost', '$0')}"
        )
        await interaction.response.send_message(detail, ephemeral=True)


async def run_autonomous_engine(bot, channel_id: int):
    """
    Main autonomous loop. Runs every 4 hours.
    Posts daily plan, executes auto actions, surfaces approvals.
    """
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        logger.error(f"Autonomous engine channel {channel_id} not found")
        return

    if not hasattr(bot, 'autonomous_queue'):
        bot.autonomous_queue = []

    logger.info("Autonomous Engine running")

    # Post first plan immediately
    first_run = True

    while not bot.is_closed():
        try:
            if first_run:
                await asyncio.sleep(30)  # Wait for bot to fully start
                first_run = False

            ventures    = getattr(bot, 'active_ventures', [])
            revenue_log = getattr(bot, 'revenue_log', {})

            # Generate daily plan
            plan = await generate_daily_plan(ventures, revenue_log)

            if plan:
                await channel.send(embed=plan_embed(plan))

                # Post approval requests for actions needing approval
                approvals = plan.get("approval_needed", [])
                for action in approvals[:3]:  # Max 3 approval requests at once
                    embed = discord.Embed(
                        title=f"✋ Approval Needed: {action.get('action', 'Action')[:80]}",
                        description=(
                            f"**Why:** {action.get('reason', 'N/A')}\n"
                            f"**Impact:** {action.get('impact', 'N/A')}\n"
                            f"**Cost:** {action.get('cost', '$0')}"
                        ),
                        color=0xffc944,
                        timestamp=datetime.utcnow()
                    )
                    view = ApprovalView(action, bot)
                    await channel.send(embed=embed, view=view)
                    await asyncio.sleep(1)

                # Execute auto actions (just log them)
                auto_actions = plan.get("auto_actions", [])
                if auto_actions:
                    action_list = "\n".join([
                        f"• {a.get('action')} ({a.get('timing', 'now')})"
                        for a in auto_actions[:5]
                    ])
                    await channel.send(
                        f"⚡ **Executing automatically:**\n{action_list}"
                    )

        except Exception as e:
            logger.error(f"Autonomous engine error: {e}")

        # Run every 6 hours
        await asyncio.sleep(6 * 60 * 60)
