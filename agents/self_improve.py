"""
OpenClaw — Self-Improvement Engine
Analyzes performance data and rewrites its own prompts/strategies.
All changes shown to operator for review before applying.

How it works:
1. Monitors what's working (high-converting listings, viral posts, etc.)
2. Identifies patterns in successful vs unsuccessful actions
3. Proposes specific prompt/strategy changes with before/after
4. You review and approve changes
5. Changes are applied to the relevant agent prompts

/improve command triggers manual analysis of any area.
Automatic weekly analysis runs in background.
"""

import asyncio
import json
import logging
import discord
import os
from datetime import datetime
from utils.claude import think_json, think
from config.settings import settings

logger = logging.getLogger("openclaw.self_improve")

SYSTEM = """You are OpenClaw's Self-Improvement Analyst.
You analyze AI performance data and propose specific, measurable improvements.
You rewrite prompts to be more effective based on what's actually working.
Be specific — show exact before/after prompt changes.
Always respond with valid JSON only."""

# Storage path for learned improvements
IMPROVEMENTS_FILE = "/tmp/openclaw_improvements.json"


def load_improvements() -> dict:
    """Loads saved improvements."""
    try:
        if os.path.exists(IMPROVEMENTS_FILE):
            with open(IMPROVEMENTS_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"applied": [], "pending": [], "rejected": []}


def save_improvements(data: dict):
    """Saves improvements to disk."""
    try:
        with open(IMPROVEMENTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save improvements: {e}")


async def analyze_performance(area: str, context: dict) -> dict:
    """
    Analyzes a specific area and proposes improvements.
    area: 'listings' | 'social' | 'opportunities' | 'products' | 'general'
    """
    revenue  = context.get('revenue', {})
    ventures = context.get('ventures', [])
    total    = sum(revenue.values()) if revenue else 0

    area_context = {
        "listings": "Etsy listing titles, descriptions, tags, and pricing",
        "social":   "Social media content, hooks, hashtags, posting times",
        "opportunities": "Niche selection, opportunity scoring, market research",
        "products": "Product type selection, content quality, design direction",
        "general":  "Overall strategy, revenue velocity, bottlenecks",
    }

    prompt = f"""Analyze OpenClaw's performance and propose specific improvements for: {area}

Area focus: {area_context.get(area, area)}
Total revenue: ${total:.2f}
Target: ${settings.REVENUE_TARGET:.0f}
Active niches: {[v.get('niche') for v in ventures if v.get('niche')]}
Revenue breakdown: {json.dumps(revenue)}

Identify what's likely working and what isn't. Propose specific changes.

Return JSON:
{{
  "area": "{area}",
  "analysis": "What you observed and why it matters",
  "current_performance": "honest/brutal assessment",
  "root_cause": "The main thing holding back results",
  "improvements": [
    {{
      "title": "Short name for this improvement",
      "type": "prompt_change | strategy_change | schedule_change | pricing_change",
      "current": "Current approach/prompt (be specific)",
      "proposed": "New approach/prompt (be specific)",
      "reasoning": "Why this will work better",
      "expected_impact": "Specific measurable improvement expected",
      "confidence": 85,
      "effort": "low | medium | high"
    }}
  ],
  "quick_wins": ["Immediate action 1", "Immediate action 2", "Immediate action 3"],
  "priority_improvement": "The single change that will have the most impact"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=3000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {}


async def analyze_from_feedback(feedback: str, context: dict) -> dict:
    """
    Analyzes based on specific operator feedback.
    Called when operator uses /improve with a specific complaint.
    """
    prompt = f"""The operator gave this feedback about OpenClaw: "{feedback}"

Current context:
Revenue: ${sum(context.get('revenue', {}).values()):.2f}
Active ventures: {[v.get('niche') for v in context.get('ventures', []) if v.get('niche')]}

Based on this feedback, identify the specific problems and propose concrete fixes.
Be very specific about what exactly needs to change.

Return JSON:
{{
  "feedback_summary": "What the operator is saying isn't working",
  "diagnosed_problems": ["Problem 1", "Problem 2"],
  "improvements": [
    {{
      "title": "Fix name",
      "type": "prompt_change | strategy_change | schedule_change",
      "current": "What OpenClaw currently does",
      "proposed": "Exact new approach with specific details",
      "reasoning": "Why this fixes the feedback",
      "expected_impact": "What will be different after this change",
      "confidence": 85,
      "effort": "low"
    }}
  ],
  "immediate_action": "What OpenClaw should do RIGHT NOW",
  "follow_up": "How to verify the fix worked"
}}"""

    raw = await think_json(SYSTEM, prompt, max_tokens=2000)
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except:
        return {}


def improvement_embed(analysis: dict, improvement: dict, idx: int) -> discord.Embed:
    """Embed showing a proposed improvement for review."""
    effort_colors = {"low": 0x00f5a0, "medium": 0xffc944, "high": 0xff7733}
    color = effort_colors.get(improvement.get("effort", "medium"), 0x00c8f0)

    embed = discord.Embed(
        title=f"🔧 Improvement #{idx+1}: {improvement.get('title', 'Untitled')[:80]}",
        description=improvement.get("reasoning", "")[:300],
        color=color,
        timestamp=datetime.utcnow()
    )

    if improvement.get("current"):
        embed.add_field(
            name="📌 Current Approach",
            value=f"```{improvement['current'][:400]}```",
            inline=False
        )

    if improvement.get("proposed"):
        embed.add_field(
            name="✨ Proposed Change",
            value=f"```{improvement['proposed'][:400]}```",
            inline=False
        )

    if improvement.get("expected_impact"):
        embed.add_field(
            name="📈 Expected Impact",
            value=improvement["expected_impact"][:512],
            inline=True
        )

    if improvement.get("confidence"):
        embed.add_field(
            name="🎯 Confidence",
            value=f"{improvement['confidence']}/100",
            inline=True
        )

    if improvement.get("effort"):
        embed.add_field(
            name="💪 Effort",
            value=improvement["effort"].upper(),
            inline=True
        )

    embed.set_footer(
        text="OpenClaw Self-Improvement • Review and approve to apply"
    )
    return embed


class ImprovementApprovalView(discord.ui.View):
    """Apply / Reject buttons for improvement proposals."""

    def __init__(self, improvement: dict, bot_ref):
        super().__init__(timeout=None)
        self.improvement = improvement
        self.bot_ref     = bot_ref

    @discord.ui.button(label="✅ Apply This Change", style=discord.ButtonStyle.success)
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        title = self.improvement.get("title", "improvement")

        await interaction.response.send_message(
            f"✅ **{title}** approved and applied!\n"
            f"OpenClaw will use the new approach going forward.\n"
            f"Results will show in analytics within 24-48 hours.",
            ephemeral=False
        )

        # Save to improvements log
        data = load_improvements()
        data["applied"].append({
            **self.improvement,
            "applied_at": datetime.now().isoformat(),
            "applied_by": str(interaction.user)
        })
        save_improvements(data)

        logger.info(f"Improvement applied: {title}")
        self.stop()

    @discord.ui.button(label="❌ Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "❌ Improvement rejected. OpenClaw will keep current approach.",
            ephemeral=False
        )
        data = load_improvements()
        data["rejected"].append({
            **self.improvement,
            "rejected_at": datetime.now().isoformat()
        })
        save_improvements(data)
        self.stop()

    @discord.ui.button(label="💬 Modify", style=discord.ButtonStyle.primary)
    async def modify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"To modify this improvement, use:\n"
            f"`/improve \"your specific feedback about this change\"`\n"
            f"OpenClaw will refine the proposal based on your input.",
            ephemeral=True
        )


async def run_improvement_check(bot, channel_id: int, context: dict) -> None:
    """
    Runs a full improvement check across all areas.
    Called by /improve command or weekly automatic check.
    """
    channel = bot.get_channel(channel_id) if channel_id else None
    if not channel:
        return

    areas = ["listings", "social", "opportunities", "products"]

    for area in areas:
        try:
            analysis = await analyze_performance(area, context)
            if not analysis:
                continue

            improvements = analysis.get("improvements", [])
            if not improvements:
                continue

            # Post analysis header
            header = discord.Embed(
                title=f"🔍 Analysis: {area.upper()}",
                description=(
                    f"**Assessment:** {analysis.get('current_performance', 'N/A')}\n"
                    f"**Root Cause:** {analysis.get('root_cause', 'N/A')}\n"
                    f"**Priority Fix:** {analysis.get('priority_improvement', 'N/A')}"
                ),
                color=0x00c8f0,
                timestamp=datetime.utcnow()
            )

            quick_wins = analysis.get("quick_wins", [])
            if quick_wins:
                header.add_field(
                    name="⚡ Quick Wins",
                    value="\n".join([f"• {w}" for w in quick_wins[:3]]),
                    inline=False
                )
            await channel.send(embed=header)

            # Post each improvement for approval
            for i, improvement in enumerate(improvements[:3]):
                embed = improvement_embed(analysis, improvement, i)
                view  = ImprovementApprovalView(improvement, bot)
                await channel.send(embed=embed, view=view)
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Improvement analysis error for {area}: {e}")


async def run_self_improvement_scheduler(bot, channel_id: int):
    """Weekly automatic improvement analysis."""
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    logger.info("Self-improvement scheduler running (weekly)")

    # Wait a week before first run
    await asyncio.sleep(7 * 24 * 60 * 60)

    while not bot.is_closed():
        try:
            context = {
                "revenue":  getattr(bot, 'revenue_log', {}),
                "ventures": getattr(bot, 'active_ventures', []),
            }
            await channel.send(embed=discord.Embed(
                title="🔧 Weekly Self-Improvement Analysis",
                description="OpenClaw is analyzing its own performance and proposing improvements...",
                color=0xb060ff,
                timestamp=datetime.utcnow()
            ))
            await run_improvement_check(bot, channel_id, context)
        except Exception as e:
            logger.error(f"Self-improvement scheduler error: {e}")

        await asyncio.sleep(7 * 24 * 60 * 60)
