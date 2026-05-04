"""
OpenClaw — API Usage Tracker
Tracks token usage and estimates costs across all AI providers.
"""

import logging
import discord
from datetime import datetime
from config.settings import settings

logger = logging.getLogger("openclaw.usage")

PRICING = {
    "claude":   {"name":"Claude Sonnet 4.6","emoji":"🟣","input":3.00, "output":15.00,"dashboard":"console.anthropic.com/usage"},
    "gpt4o":    {"name":"GPT-4o",           "emoji":"🟢","input":2.50, "output":10.00,"dashboard":"platform.openai.com/usage"},
    "gemini":   {"name":"Gemini 1.5 Pro",   "emoji":"🔵","input":1.25, "output":5.00, "dashboard":"aistudio.google.com"},
    "deepseek": {"name":"DeepSeek-Chat",    "emoji":"🟡","input":0.14, "output":0.28, "dashboard":"platform.deepseek.com/usage"},
    "glm":      {"name":"GLM-5.1",          "emoji":"⚪","input":0.50, "output":1.50, "dashboard":"z.ai/dashboard"},
}

_usage: dict = {k: {"input_tokens":0,"output_tokens":0,"calls":0} for k in PRICING}


def record_usage(model: str, input_tokens: int, output_tokens: int):
    if model in _usage:
        _usage[model]["input_tokens"]  += input_tokens
        _usage[model]["output_tokens"] += output_tokens
        _usage[model]["calls"]         += 1


def usage_embed() -> discord.Embed:
    total_cost  = sum((v["input_tokens"]/1e6*PRICING[m]["input"]) + (v["output_tokens"]/1e6*PRICING[m]["output"]) for m,v in _usage.items() if m in PRICING)
    total_calls = sum(v["calls"] for v in _usage.values())

    embed = discord.Embed(
        title="📊 API Usage & Cost Tracker",
        description=(
            f"**Session total:** ${total_cost:.4f} | **Calls:** {total_calls:,}\n"
            f"*Resets on restart — check dashboards for full billing.*"
        ),
        color=0x00c8f0,
        timestamp=datetime.utcnow()
    )

    configured = {
        "claude":   bool(settings.ANTHROPIC_API_KEY),
        "gpt4o":    bool(settings.OPENAI_API_KEY),
        "gemini":   bool(settings.GEMINI_API_KEY),
        "deepseek": bool(settings.DEEPSEEK_API_KEY),
        "glm":      bool(settings.GLM_API_KEY),
    }

    for model, p in PRICING.items():
        u    = _usage[model]
        cost = (u["input_tokens"]/1e6*p["input"]) + (u["output_tokens"]/1e6*p["output"])
        if not configured[model]:
            val = "⏭️ Not configured"
        elif u["calls"] == 0:
            val = "✅ Ready — not used yet this session"
        else:
            val = f"**${cost:.4f}** this session"

        embed.add_field(
            name=f"{p['emoji']} {p['name']}",
            value=(
                f"Cost: {val}\n"
                f"Calls: {u['calls']:,} | Tokens: {u['input_tokens']:,}in / {u['output_tokens']:,}out\n"
                f"Rate: ${p['input']:.2f}/${p['output']:.2f} per 1M\n"
                f"[Dashboard ↗](https://{p['dashboard']})"
            ),
            inline=True
        )

    embed.add_field(
        name="💡 Save Money",
        value=(
            "• `/ask @deepseek` — 20x cheaper for analysis\n"
            "• `/ask @glm` — 6x cheaper for code\n"
            "• `/ask @gemini` — best for research tasks\n"
            "• Claude → listings/copy only"
        ),
        inline=False
    )
    embed.add_field(
        name="📋 Full Billing Dashboards",
        value=(
            "• [Anthropic](https://console.anthropic.com/usage) "
            "• [OpenAI](https://platform.openai.com/usage) "
            "• [DeepSeek](https://platform.deepseek.com/usage) "
            "• [Gemini](https://aistudio.google.com) "
            "• [GLM](https://z.ai/dashboard)"
        ),
        inline=False
    )
    embed.set_footer(text="Session costs only — check dashboards for total spend")
    return embed
