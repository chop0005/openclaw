"""OpenClaw Settings — loaded from Railway environment variables"""
import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Settings:
    # Discord
    DISCORD_TOKEN: str        = field(default_factory=lambda: os.getenv("DISCORD_TOKEN", ""))
    DISCORD_GUILD_ID: int     = field(default_factory=lambda: int(os.getenv("DISCORD_GUILD_ID", "0")))

    # AI
    ANTHROPIC_API_KEY: str    = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    CLAUDE_MODEL: str         = "claude-sonnet-4-6"

    # Goal
    CAPITAL_BUDGET: float     = field(default_factory=lambda: float(os.getenv("CAPITAL_BUDGET", "50")))
    REVENUE_TARGET: float     = field(default_factory=lambda: float(os.getenv("REVENUE_TARGET", "500")))
    TARGET_DAYS: int          = field(default_factory=lambda: int(os.getenv("TARGET_DAYS", "30")))

    # Agent schedules (minutes)
    TREND_INTERVAL: int       = field(default_factory=lambda: int(os.getenv("TREND_INTERVAL", "60")))
    OPPORTUNITY_INTERVAL: int = field(default_factory=lambda: int(os.getenv("OPPORTUNITY_INTERVAL", "240")))
    LISTING_INTERVAL: int     = field(default_factory=lambda: int(os.getenv("LISTING_INTERVAL", "360")))
    REVENUE_INTERVAL: int     = field(default_factory=lambda: int(os.getenv("REVENUE_INTERVAL", "1440")))  # daily

    # Optional platform keys (add as you set up accounts)
    ETSY_API_KEY: Optional[str]       = field(default_factory=lambda: os.getenv("ETSY_API_KEY"))
    GUMROAD_ACCESS_TOKEN: Optional[str] = field(default_factory=lambda: os.getenv("GUMROAD_ACCESS_TOKEN"))

settings = Settings()
