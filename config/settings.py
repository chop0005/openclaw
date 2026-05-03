"""OpenClaw Settings — loaded from Railway environment variables"""
import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Settings:
    # ── Discord ───────────────────────────────────────────────
    DISCORD_TOKEN: str              = field(default_factory=lambda: os.getenv("DISCORD_TOKEN", ""))
    DISCORD_GUILD_ID: int           = field(default_factory=lambda: int(os.getenv("DISCORD_GUILD_ID", "0")))

    # ── Claude (Anthropic) ────────────────────────────────────
    ANTHROPIC_API_KEY: str          = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    CLAUDE_MODEL: str               = "claude-sonnet-4-6"

    # ── OpenAI ────────────────────────────────────────────────
    OPENAI_API_KEY: Optional[str]   = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))

    # ── Gemini ────────────────────────────────────────────────
    GEMINI_API_KEY: Optional[str]   = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))

    # ── DeepSeek ──────────────────────────────────────────────
    DEEPSEEK_API_KEY: Optional[str] = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY"))

    # ── GLM / Z.ai ────────────────────────────────────────────
    GLM_API_KEY: Optional[str]      = field(default_factory=lambda: os.getenv("GLM_API_KEY"))
    GLM_CODE_MODEL: str             = field(default_factory=lambda: os.getenv("GLM_CODE_MODEL", "GLM-5.1"))
    GLM_ENDPOINT: str               = "https://api.z.ai/api/paas/v4/messages"

    # ── Etsy ──────────────────────────────────────────────────
    ETSY_API_KEY: Optional[str]         = field(default_factory=lambda: os.getenv("ETSY_API_KEY"))
    ETSY_ACCESS_TOKEN: Optional[str]    = field(default_factory=lambda: os.getenv("ETSY_ACCESS_TOKEN"))
    ETSY_SHOP_ID: Optional[str]         = field(default_factory=lambda: os.getenv("ETSY_SHOP_ID"))

    # ── Gumroad ───────────────────────────────────────────────
    GUMROAD_ACCESS_TOKEN: Optional[str] = field(default_factory=lambda: os.getenv("GUMROAD_ACCESS_TOKEN"))

    # ── Pinterest ─────────────────────────────────────────────
    PINTEREST_ACCESS_TOKEN: Optional[str] = field(default_factory=lambda: os.getenv("PINTEREST_ACCESS_TOKEN"))
    PINTEREST_BOARD_ID: Optional[str]     = field(default_factory=lambda: os.getenv("PINTEREST_BOARD_ID"))

    # ── Beehiiv (newsletter) ──────────────────────────────────
    BEEHIIV_API_KEY: Optional[str]        = field(default_factory=lambda: os.getenv("BEEHIIV_API_KEY"))
    BEEHIIV_PUBLICATION_ID: Optional[str] = field(default_factory=lambda: os.getenv("BEEHIIV_PUBLICATION_ID"))

    # ── Goal ──────────────────────────────────────────────────
    CAPITAL_BUDGET: float           = field(default_factory=lambda: float(os.getenv("CAPITAL_BUDGET", "50")))
    REVENUE_TARGET: float           = field(default_factory=lambda: float(os.getenv("REVENUE_TARGET", "500")))
    TARGET_DAYS: int                = field(default_factory=lambda: int(os.getenv("TARGET_DAYS", "30")))

    # ── Agent schedules (minutes) ─────────────────────────────
    OPPORTUNITY_INTERVAL: int       = field(default_factory=lambda: int(os.getenv("OPPORTUNITY_INTERVAL", "240")))
    REVENUE_INTERVAL: int           = field(default_factory=lambda: int(os.getenv("REVENUE_INTERVAL", "1440")))

settings = Settings()
