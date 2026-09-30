"""Configuration loader for VideoBot."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    def __init__(self) -> None:
        self.bot_token: str = os.getenv("BOT_TOKEN", "")
        raw = os.getenv("ADMIN_IDS", "")
        self.admin_ids = tuple(
            int(x.strip()) for x in raw.split(",") if x.strip().isdigit()
        )
        self.daily_limit: int = _int("DAILY_LIMIT", 5)
        self.referrals_needed: int = _int("REFERRALS_NEEDED", 3)
        self.delete_after: int = _int("DELETE_AFTER", 600)  # seconds
        self.db_path: str = os.getenv("DB_PATH", "videobot.db")
        self.database_url: str = os.getenv("DATABASE_URL", "")
        # Webhook mode (Render etc.): set WEBHOOK_URL to the public base URL
        # e.g. https://videobot.onrender.com — otherwise polling is used.
        self.webhook_url: str = os.getenv("WEBHOOK_URL", "").rstrip("/")
        self.port: int = _int("PORT", 8443)
