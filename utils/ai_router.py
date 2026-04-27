"""
OpenClaw — Multi-Model AI Router
Routes tasks to the best model automatically, or lets you pick manually.

Models:
  claude    → Claude Sonnet 4.6   — strategy, copy, listings, business intelligence
  gpt4o     → GPT-4o              — general chat, analysis, versatile
  gemini    → Gemini 1.5 Pro      — research, long context, web-aware
  deepseek  → DeepSeek-Chat       — cheap reasoning, analysis, math
  glm       → GLM-5.1             — code generation (via Z.ai)

Auto-routing rules:
  copy/listings/etsy/strategy → claude
  code/build/technical        → glm → fallback claude
  research/trends/search      → gemini → fallback claude
  math/analysis/data          → deepseek → fallback claude
  general chat                → gpt4o → fallback claude
"""

import aiohttp
import json
import logging
from typing import Optional
from config.settings import settings

logger = logging.getLogger("openclaw.ai_router")

# ── Model definitions ─────────────────────────────────────────

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

# ── Auto-router ───────────────────────────────────────────────

def pick_model(prompt: str, force: Optional[str] = None) -> str:
    """
    Picks the best model for a given prompt.
    Returns model key string.
    """
    if force and force in MODELS:
        return force

    prompt_lower = prompt.lower()

    # Score each model
    scores = {key: 0 for key in MODELS}
    for key, model in MODELS.items():
        for keyword in model["best_for"]:
            if keyword in prompt_lower:
                scores[key] += 1

    # Check API availability
    available = get_available_models()

    # Pick highest score among available models
    best = max(
        [(k, v) for k, v in scores.items() if k in available],
        key=lambda x: x[1],
        default=("claude", 0)
    )

    # If no clear winner, default to gpt4o for chat, claude for business
    if best[1] == 0:
        if "gpt4o" in available:
            return "gpt4o"
        return "claude"

    return best[0]


def get_available_models() -> list[str]:
    """Returns list of model keys that have API keys configured."""
    available = []
    if settings.ANTHROPIC_API_KEY:   available.append("claude")
    if settings.OPENAI_API_KEY:      available.append("gpt4o")
    if settings.GEMINI_API_KEY:      available.append("gemini")
    if settings.DEEPSEEK_API_KEY:    available.append("deepseek")
    if settings.GLM_API_KEY:         available.append("glm")
    return available


# ── Model callers ─────────────────────────────────────────────

async def call_claude(system: str, prompt: str, max_tokens: int = 2000) -> str:
    import anthropic
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
        payload = {
            "model": "gpt-4o",
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt}
            ]
        }
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type":  "application/json"
        }
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data["choices"][0]["message"]["content"]
            else:
                raise Exception(f"OpenAI error {resp.status}: {data.get('error', {}).get('message', 'Unknown')}")


async def call_gemini(system: str, prompt: str, max_tokens: int = 2000) -> str:
    async with aiohttp.ClientSession() as session:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens}
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={settings.GEMINI_API_KEY}"
        async with session.post(
            url, json=payload,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                raise Exception(f"Gemini error {resp.status}: {data.get('error', {}).get('message', 'Unknown')}")


async def call_deepseek(system: str, prompt: str, max_tokens: int = 2000) -> str:
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "deepseek-chat",
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt}
            ]
        }
        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type":  "application/json"
        }
        async with session.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data["choices"][0]["message"]["content"]
            else:
                raise Exception(f"DeepSeek error {resp.status}: {data.get('error', {}).get('message', 'Unknown')}")


async def call_glm(system: str, prompt: str, max_tokens: int = 2000) -> str:
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": settings.GLM_CODE_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}]
        }
        headers = {
            "Authorization": f"Bearer {settings.GLM_API_KEY}",
            "Content-Type":  "application/json",
            "anthropic-version": "2023-06-01"
        }
        async with session.post(
            settings.GLM_ENDPOINT,
            json=payload, headers=headers,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                if "content" in data:
                    return data["content"][0]["text"]
                elif "choices" in data:
                    return data["choices"][0]["message"]["content"]
            raise Exception(f"GLM error {resp.status}")


# ── Main router function ──────────────────────────────────────

async def route(
    prompt: str,
    system: str = "",
    force_model: Optional[str] = None,
    max_tokens: int = 2000,
    bot_context: Optional[dict] = None
) -> tuple[str, str]:
    """
    Routes prompt to best model. Returns (response_text, model_key_used).
    bot_context: optional dict with revenue, ventures etc. for context injection.
    """
    model_key = pick_model(prompt, force_model)
    available = get_available_models()

    # Build context-aware system prompt
    base_system = system or build_system_prompt(bot_context)

    # Fallback chain: picked model → claude → gpt4o → whatever's available
    fallback_chain = [model_key]
    for fallback in ["claude", "gpt4o", "deepseek", "gemini", "glm"]:
        if fallback not in fallback_chain and fallback in available:
            fallback_chain.append(fallback)

    last_error = None
    for attempt_key in fallback_chain:
        if attempt_key not in available:
            continue
        try:
            logger.info(f"Routing to {attempt_key}: {prompt[:60]}...")
            callers = {
                "claude":   call_claude,
                "gpt4o":    call_openai,
                "gemini":   call_gemini,
                "deepseek": call_deepseek,
                "glm":      call_glm,
            }
            result = await callers[attempt_key](base_system, prompt, max_tokens)
            return result, attempt_key
        except Exception as e:
            last_error = e
            logger.warning(f"{attempt_key} failed: {e} — trying fallback")
            continue

    return f"❌ All models failed. Last error: {last_error}", "error"


def build_system_prompt(context: Optional[dict] = None) -> str:
    """Builds a context-aware system prompt with store data."""
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

    # Inject live store context
    revenue   = context.get('revenue', {})
    ventures  = context.get('ventures', [])
    total_rev = sum(revenue.values()) if revenue else 0
    target    = context.get('target', 500)
    days_left = context.get('days_left', 30)

    context_str = f"\n\n**Current Store Status:**"
    context_str += f"\n- Total revenue: ${total_rev:.2f} / ${target:.0f} target"
    context_str += f"\n- Days remaining: {days_left}"

    if revenue:
        context_str += f"\n- Products with sales: {', '.join([f'{k} (${v:.2f})' for k, v in revenue.items()])}"

    if ventures:
        active = [v.get('niche') for v in ventures if v.get('niche')]
        if active:
            context_str += f"\n- Active niches: {', '.join(active)}"

    return base + context_str
