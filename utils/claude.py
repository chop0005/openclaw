"""Claude API — OpenClaw's reasoning engine"""
import anthropic
import logging
from config.settings import settings

logger = logging.getLogger("openclaw.claude")
_client = None

def get_client():
    global _client
    if not _client:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client

async def think(system: str, prompt: str, max_tokens: int = 2000) -> str:
    try:
        msg = get_client().messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return f"[Error: {e}]"

async def think_json(system: str, prompt: str, max_tokens: int = 2000) -> str:
    return await think(
        system + "\n\nCRITICAL: Return ONLY raw valid JSON. No markdown, no backticks, no explanation.",
        prompt,
        max_tokens
    )
