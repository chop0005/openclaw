"""
OpenClaw — AI Chat Agent
Handles the #ai-chat channel. Routes messages to best available model.
All model logic is inline — no external router dependency.
"""

import asyncio
import logging
import discord
from datetime import datetime
from collections import defaultdict
from config.settings import settings

logger = logging.getLogger("openclaw.ai_chat")

_history: dict = defaultdict(list)
MAX_HISTORY = 10

# Inline model definitions — no import needed
MODELS = {
    "claude":   {"name": "Claude Sonnet 4.6", "emoji": "🟣", "best_for": ["copy","listing","strategy","etsy","brand","niche","product"]},
    "gpt4o":    {"name": "GPT-4o",            "emoji": "🟢", "best_for": ["chat","general","explain","help","what","how","why"]},
    "gemini":   {"name": "Gemini 1.5 Pro",    "emoji": "🔵", "best_for": ["research","trend","search","find","compare","news","market"]},
    "deepseek": {"name": "DeepSeek-Chat",     "emoji": "🟡", "best_for": ["analyze","calculate","data","math","reason","plan","estimate"]},
    "glm":      {"name": "GLM-5.1",           "emoji": "⚪", "best_for": ["code","build","script","function","debug","program","develop"]},
}


def get_available() -> list:
    a = []
    if settings.ANTHROPIC_API_KEY:  a.append("claude")
    if settings.OPENAI_API_KEY:     a.append("gpt4o")
    if settings.GEMINI_API_KEY:     a.append("gemini")
    if settings.DEEPSEEK_API_KEY:   a.append("deepseek")
    if settings.GLM_API_KEY:        a.append("glm")
    return a


def pick(prompt: str) -> str:
    pl = prompt.lower()
    scores = {k: sum(1 for kw in v["best_for"] if kw in pl) for k, v in MODELS.items()}
    available = get_available()
    best = max([(k, s) for k, s in scores.items() if k in available], key=lambda x: x[1], default=("claude", 0))
    if best[1] == 0:
        return "gpt4o" if "gpt4o" in available else "claude"
    return best[0]


async def call_model(model_key: str, system: str, prompt: str) -> str:
    import aiohttp, anthropic

    if model_key == "claude":
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=settings.CLAUDE_MODEL, max_tokens=1500,
            system=system, messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text

    elif model_key == "gpt4o":
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.openai.com/v1/chat/completions",
                json={"model": "gpt-4o", "max_tokens": 1500,
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as r:
                d = await r.json()
                return d["choices"][0]["message"]["content"]

    elif model_key == "gemini":
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={settings.GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}],
                      "generationConfig": {"maxOutputTokens": 1500}},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as r:
                d = await r.json()
                return d["candidates"][0]["content"]["parts"][0]["text"]

    elif model_key == "deepseek":
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.deepseek.com/v1/chat/completions",
                json={"model": "deepseek-chat", "max_tokens": 1500,
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]},
                headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as r:
                d = await r.json()
                return d["choices"][0]["message"]["content"]

    elif model_key == "glm":
        async with aiohttp.ClientSession() as s:
            async with s.post(
                settings.GLM_ENDPOINT,
                json={"model": settings.GLM_CODE_MODEL, "max_tokens": 1500,
                      "system": system, "messages": [{"role": "user", "content": prompt}]},
                headers={"Authorization": f"Bearer {settings.GLM_API_KEY}",
                         "Content-Type": "application/json", "anthropic-version": "2023-06-01"},
                timeout=aiohttp.ClientTimeout(total=120)
            ) as r:
                d = await r.json()
                if "content" in d: return d["content"][0]["text"]
                return d["choices"][0]["message"]["content"]

    raise Exception(f"Unknown model: {model_key}")


def build_context(bot) -> str:
    revenue  = getattr(bot, 'revenue_log', {})
    ventures = getattr(bot, 'active_ventures', [])
    total    = sum(revenue.values()) if revenue else 0
    base = (
        "You are OpenClaw — autonomous business engine in Discord. "
        "Help the operator build digital product businesses on Etsy/Gumroad. "
        "Be direct and practical. Goal: $500 in 30 days."
    )
    if total > 0:
        base += f" Current revenue: ${total:.2f}/${settings.REVENUE_TARGET:.0f}."
    if ventures:
        niches = [v.get('niche') for v in ventures if v.get('niche')]
        if niches:
            base += f" Active niches: {', '.join(niches)}."
    return base


def model_status_embed(bot) -> discord.Embed:
    available = get_available()
    embed = discord.Embed(
        title="🤖 AI Models — OpenClaw",
        description="Your full AI stack. Chat in #ai-chat or use /ask.",
        color=0x00c8f0, timestamp=datetime.utcnow()
    )
    for key, model in MODELS.items():
        status = "✅ Connected" if key in available else "⚠️ No API key"
        embed.add_field(name=f"{model['emoji']} {model['name']}", value=status, inline=True)
    embed.add_field(
        name="🔀 Auto-routing",
        value="🟣 Claude → listings/copy\n🟢 GPT-4o → chat\n🔵 Gemini → research\n🟡 DeepSeek → analysis\n⚪ GLM → code",
        inline=False
    )
    return embed


async def handle_chat_message(message: discord.Message, bot):
    if message.author.bot:
        return
    content = message.content.strip()
    if not content:
        return

    async with message.channel.typing():
        model_key = pick(content)
        system    = build_context(bot)
        available = get_available()

        # Try picked model, fallback through available ones
        chain = [model_key] + [m for m in ["claude","gpt4o","deepseek","gemini","glm"] if m != model_key and m in available]

        response = None
        used = model_key
        for key in chain:
            if key not in available:
                continue
            try:
                response = await call_model(key, system, content)
                used = key
                break
            except Exception as e:
                logger.warning(f"{key} failed: {e}")
                continue

        if not response:
            response = "❌ All models failed. Check your API keys in Railway."
            used = "error"

        info = MODELS.get(used, {"emoji": "❓", "name": "Unknown"})
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for i, chunk in enumerate(chunks):
            suffix = f"\n\n{info['emoji']} *{info['name']}*" if i == 0 else ""
            await message.channel.send(chunk + suffix)


async def run_ai_chat_monitor(bot, channel_id: int):
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)
    if not channel:
        logger.error(f"AI chat channel {channel_id} not found")
        return

    available = get_available()
    model_list = " • ".join([f"{MODELS[k]['emoji']} {MODELS[k]['name']}" for k in available if k in MODELS])

    embed = discord.Embed(
        title="🤖 AI Assistant Ready",
        description=(
            f"Chat with your full AI stack right here.\n\n"
            f"**Active:** {model_list or 'Configure API keys in Railway'}\n\n"
            f"Just type — I'll route to the best model automatically.\n"
            f"Or use `/ask` anywhere in the server."
        ),
        color=0x00c8f0, timestamp=datetime.utcnow()
    )
    await channel.send(embed=embed)
    logger.info(f"AI Chat ready on #{channel.name}")

    while not bot.is_closed():
        await asyncio.sleep(60)
