"""
OpenClaw — AI Router
Two models, one interface:
  think()       → Claude Sonnet  (business intelligence, copy, strategy)
  think_code()  → GLM-5.1        (code generation, technical tasks)
  think_json()  → Claude Sonnet  (structured data, opportunity research)

If GLM key is missing, code tasks fall back to Claude automatically.
"""

import anthropic
import aiohttp
import json
import logging
from config.settings import settings

logger = logging.getLogger("openclaw.ai")

# ── Claude client ─────────────────────────────────────────────
_claude_client = None

def get_claude():
    global _claude_client
    if not _claude_client:
        _claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _claude_client


# ── Claude — business intelligence, copy, strategy ───────────
async def think(system: str, prompt: str, max_tokens: int = 2000) -> str:
    """
    Claude Sonnet — used for:
    - Opportunity scanning & niche research
    - Etsy listing copy & SEO
    - Launch strategy & planning
    - Revenue analysis
    """
    try:
        msg = get_claude().messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return f"[Claude error: {e}]"


async def think_json(system: str, prompt: str, max_tokens: int = 2000) -> str:
    """Claude Sonnet with JSON enforcement — for structured research output."""
    return await think(
        system + "\n\nCRITICAL: Return ONLY raw valid JSON. No markdown, no backticks, no explanation.",
        prompt,
        max_tokens
    )


# ── GLM — code generation, technical tasks ───────────────────
async def think_code(system: str, prompt: str, max_tokens: int = 4000) -> str:
    """
    GLM-5.1 via Z.ai — used for:
    - Generating app code (React, Python, etc.)
    - Chrome extension code
    - Technical spec generation
    - Debugging and refactoring

    Falls back to Claude if GLM key is not set.
    Cost: ~5x cheaper than Claude for code tasks.
    """
    # Fallback to Claude if no GLM key
    if not settings.GLM_API_KEY:
        logger.info("GLM key not set — falling back to Claude for code task")
        return await think(system, prompt, max_tokens)

    try:
        # GLM supports Anthropic API format via their endpoint
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": settings.GLM_CODE_MODEL,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": prompt}]
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.GLM_API_KEY}",
                "anthropic-version": "2023-06-01"
            }
            async with session.post(
                settings.GLM_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Handle both Anthropic and OpenAI response formats
                    if "content" in data:
                        # Anthropic format
                        return data["content"][0]["text"]
                    elif "choices" in data:
                        # OpenAI format
                        return data["choices"][0]["message"]["content"]
                    else:
                        logger.error(f"Unexpected GLM response format: {data}")
                        return await think(system, prompt, max_tokens)
                else:
                    error_text = await resp.text()
                    logger.error(f"GLM API error {resp.status}: {error_text}")
                    logger.info("GLM failed — falling back to Claude")
                    return await think(system, prompt, max_tokens)

    except Exception as e:
        logger.error(f"GLM request error: {e} — falling back to Claude")
        return await think(system, prompt, max_tokens)


async def think_code_json(system: str, prompt: str, max_tokens: int = 4000) -> str:
    """GLM with JSON enforcement — for structured code/technical output."""
    return await think_code(
        system + "\n\nCRITICAL: Return ONLY raw valid JSON. No markdown, no backticks, no explanation.",
        prompt,
        max_tokens
    )
