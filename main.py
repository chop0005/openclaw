"""
OpenClaw — Autonomous Business Engine
Starts both the Discord bot and a lightweight web server.
Web server handles: Etsy OAuth callback, health checks.
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
    logger.info("🦾 OpenClaw starting...")

    if not settings.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN missing. Add to Railway variables.")
        return
    if not settings.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY missing. Add to Railway variables.")
        return
    if not settings.DISCORD_GUILD_ID:
        logger.error("DISCORD_GUILD_ID missing. Add to Railway variables.")
        return

    # Start web server (handles Etsy OAuth + health checks)
    try:
        from ventures.etsy_oauth import start_web_server
        web_runner = await start_web_server(settings.PORT)
        logger.info(f"✅ Web server on port {settings.PORT}")
    except ImportError:
        web_runner = None
        logger.warning("Web server not available — Etsy OAuth disabled")
    except Exception as e:
        web_runner = None
        logger.warning(f"Web server failed to start: {e}")

    # Start Discord bot
    bot = create_bot()
    try:
        await bot.start(settings.DISCORD_TOKEN)
    finally:
        if web_runner:
            await web_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
