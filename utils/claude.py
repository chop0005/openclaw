"""
OpenClaw — AI Router + Model Callers
All AI functionality in one file. No separate modules to go missing.

Models:
  claude    → Claude Sonnet 4.6   (strategy, copy, listings)
  gpt4o     → GPT-4o              (general chat)
  gemini    → Gemini 1.5 Pro      (research, trends)
  deepseek  → DeepSeek-Chat       (analysis, reasoning)
  glm       → GLM-5.1             (code generation)
"""

import aiohttp
import logging
import anthropic
from typing import Optional
from config.settings import settings

logger = logging.getLogger("openclaw.ai")

# ── Model registry ────────────────────────────────────────────

MODELS = {
    "claude": {
        "name":        "Claude Sonnet 4.6",
        "emoji":       "🟣",
        "description": "Strategy, copy, business intelligence",
        "best_for":    ["copy", "listing", "strategy", "etsy", "brand", "niche", "product"],
        "provider":    "anthropic",
    },
    "gpt4o": {
        "name":        "GPT-4o",
        "emoji":       "🟢",
        "description": "General chat, analysis, versatile",
        "best_for":    ["chat", "general", "explain", "help", "what", "how", "why"],
        "provider":    "openai",
    },
    "gemini": {
        "name":        "Gemini 1.5 Pro",
        "emoji":       "🔵",
        "description": "Research, trends, long context",
        "best_for":    ["research", "trend", "search", "find", "compare", "news", "market"],
        "provider":    "google",
    },
    "deepseek": {
        "name":        "DeepSeek-Chat",
        "emoji":       "🟡",
        "description": "Reasoning, analysis, math",
        "best_for":    ["analyze", "calculate", "data", "math", "reason", "plan", "estimate"],
        "provider":    "deepseek",
    },
    "glm": {
        "name":        "GLM-5.1",
        "emoji":       "⚪",
        "description": "Code generation",
        "best_for":    ["code", "build", "script", "function", "debug", "program", "develop"],
        "provider":    "glm",
    },
}

# ── Availability ──────────────────────────────────────────────

def get_available_models() -> list:
    available = []
    if settings.ANTHROPIC_API_KEY:  available.append("claude")
    if settings.OPENAI_API_KEY:     available.append("gpt4o")
    if settings.GEMINI_API_KEY:     available.append("gemini")
    if settings.DEEPSEEK_API_KEY:   available.append("deepseek")
    if settings.GLM_API_KEY:        available.append("glm")
    return available


def pick_model(prompt: str, force: Optional[str] = None) -> str:
    if force and force in MODELS:
        return force
    prompt_lower = prompt.lower()
    scores = {key: 0 for key in MODELS}
    for key, model in MODELS.items():
        for keyword in model["best_for"]:
            if keyword in prompt_lower:
                scores[key] += 1
    available = get_available_models()
    best = max(
        [(k, v) for k, v in scores.items() if k in available],
        key=lambda x: x[1],
        default=("claude", 0)
    )
    if best[1] == 0:
        if "gpt4o" in available:
            return "gpt4o"
        return "claude"
    return best[0]


# ── Model callers ─────────────────────────────────────────────

async def call_claude(system: str, prompt: str, max_tokens: int = 2000) -> str:
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


async def call_openai(system: str, prompt: str, max_tokens: int = 2000) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": prompt}
                ]
            },
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type":  "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data["choices"][0]["message"]["content"]
            raise Exception(f"OpenAI {resp.status}: {data.get('error',{}).get('message','')}")


async def call_gemini(system: str, prompt: str, max_tokens: int = 2000) -> str:
    async with aiohttp.ClientSession() as session:
        full = f"{system}\n\n{prompt}" if system else prompt
        async with session.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={settings.GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": full}]}],
                "generationConfig": {"maxOutputTokens": max_tokens}
            },
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            raise Exception(f"Gemini {resp.status}: {data.get('error',{}).get('message','')}")


async def call_deepseek(system: str, prompt: str, max_tokens: int = 2000) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.deepseek.com/v1/chat/completions",
            json={
                "model": "deepseek-chat",
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": prompt}
                ]
            },
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type":  "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data["choices"][0]["message"]["content"]
            raise Exception(f"DeepSeek {resp.status}: {data.get('error',{}).get('message','')}")


async def call_glm(system: str, prompt: str, max_tokens: int = 2000) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            settings.GLM_ENDPOINT,
            json={
                "model": settings.GLM_CODE_MODEL,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": prompt}]
            },
            headers={
                "Authorization": f"Bearer {settings.GLM_API_KEY}",
                "Content-Type":  "application/json",
                "anthropic-version": "2023-06-01"
            },
            timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                if "content" in data:
                    return data["content"][0]["text"]
                elif "choices" in data:
                    return data["choices"][0]["message"]["content"]
            raise Exception(f"GLM {resp.status}")


# ── System prompt builder ─────────────────────────────────────

def build_system_prompt(context: Optional[dict] = None) -> str:
    base = (
        "You are OpenClaw — an autonomous business engine and AI assistant "
        "living inside a Discord server. You help the operator build and grow "
        "digital product businesses on Etsy and Gumroad.\n\n"
        "You are direct, practical, and focused on making money. "
        "You give specific, actionable advice — not generic platitudes. "
        "You know the operator's goal is $500 in 30 days via digital products."
    )
    if not context:
        return base
    revenue   = context.get('revenue', {})
    ventures  = context.get('ventures', [])
    total_rev = sum(revenue.values()) if revenue else 0
    target    = context.get('target', 500)
    days_left = context.get('days_left', 30)
    extra = f"\n\nStore Status: ${total_rev:.2f} / ${target:.0f} | {days_left} days left"
    if revenue:
        extra += f" | Products: {', '.join([f'{k}(${v:.2f})' for k, v in revenue.items()])}"
    if ventures:
        active = [v.get('niche') for v in ventures if v.get('niche')]
        if active:
            extra += f" | Niches: {', '.join(active)}"
    return base + extra


# ── Main router ───────────────────────────────────────────────

async def route(
    prompt: str,
    system: str = "",
    force_model: Optional[str] = None,
    max_tokens: int = 2000,
    bot_context: Optional[dict] = None
):
    """Routes prompt to best model. Returns (response_text, model_key_used)."""
    model_key = pick_model(prompt, force_model)
    available = get_available_models()
    base_system = system or build_system_prompt(bot_context)

    fallback_chain = [model_key]
    for fb in ["claude", "gpt4o", "deepseek", "gemini", "glm"]:
        if fb not in fallback_chain and fb in available:
            fallback_chain.append(fb)

    callers = {
        "claude":   call_claude,
        "gpt4o":    call_openai,
        "gemini":   call_gemini,
        "deepseek": call_deepseek,
        "glm":      call_glm,
    }

    last_error = None
    for key in fallback_chain:
        if key not in available:
            continue
        try:
            logger.info(f"Routing to {key}: {prompt[:50]}...")
            result = await callers[key](base_system, prompt, max_tokens)
            return result, key
        except Exception as e:
            last_error = e
            logger.warning(f"{key} failed: {e} — trying fallback")

    return f"❌ All models failed. Last error: {last_error}", "error"


# ── Legacy helpers (used by other agents) ────────────────────

async def think(system: str, prompt: str, max_tokens: int = 2000) -> str:
    """Claude only — for business intelligence tasks."""
    return await call_claude(system, prompt, max_tokens)


async def think_json(system: str, prompt: str, max_tokens: int = 2000) -> str:
    """Claude with JSON enforcement."""
    return await think(
        system + "\n\nCRITICAL: Return ONLY raw valid JSON. No markdown, no backticks, no explanation.",
        prompt, max_tokens
    )


async def think_code(system: str, prompt: str, max_tokens: int = 4000) -> str:
    """GLM for code, falls back to Claude."""
    if not settings.GLM_API_KEY:
        return await call_claude(system, prompt, max_tokens)
    try:
        return await call_glm(system, prompt, max_tokens)
    except Exception:
        return await call_claude(system, prompt, max_tokens)


async def think_code_json(system: str, prompt: str, max_tokens: int = 4000) -> str:
    return await think_code(
        system + "\n\nCRITICAL: Return ONLY raw valid JSON. No markdown, no backticks, no explanation.",
        prompt, max_tokens
    )
