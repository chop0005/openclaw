"""
OpenClaw — Money-First Autonomous Business Engine
Target: $500 in 30 days via digital products
Stack:  Railway + Discord + Claude API + Etsy/Gumroad
"""

import asyncio
import logging
from bot.discord_bot import create_bot
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("openclaw")

async def main():
    logger.info("🦾 OpenClaw starting — Target: $500 in 30 days")

    if not settings.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN missing. Add to Railway variables.")
        return
    if not settings.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY missing. Add to Railway variables.")
        return
    if not settings.DISCORD_GUILD_ID:
        logger.error("DISCORD_GUILD_ID missing. Add to Railway variables.")
        return

    bot = create_bot()
    await bot.start(settings.DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
