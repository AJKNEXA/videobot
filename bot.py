"""VideoBot: disappearing protected videos with referral-unlocked limits.

Two run modes:
- Polling (default, local dev): python bot.py
- Webhook (Render etc.): set WEBHOOK_URL=https://<service>.onrender.com
"""
import asyncio
import logging
import os

from telegram import Bot
from telegram.ext import Application

from config import Config
from db import Database
import handlers


def _sanitize_proxy_env() -> None:
    """Drop proxy vars httpx can't parse (malformed bracketed IPv6 entries)."""
    for var in ("NO_PROXY", "no_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        val = os.environ.get(var, "")
        if "[" in val or "]" in val:
            del os.environ[var]


async def _delete_webhook(token: str) -> None:
    """Clear any stale webhook so polling receives updates."""
    bot = Bot(token)
    await bot.initialize()
    try:
        await bot.delete_webhook()
    finally:
        await bot.shutdown()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    # httpx logs full request URLs (which contain the bot token) — quiet it.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    _sanitize_proxy_env()
    cfg = Config()
    if not cfg.bot_token:
        print("BOT_TOKEN not found! Create a .env file (see .env.example).")
        return
    db = Database(cfg.db_path, dsn=cfg.database_url or None)
    app = Application.builder().token(cfg.bot_token).build()
    app.bot_data["db"] = db
    app.bot_data["cfg"] = cfg
    handlers.register(app)
    log = logging.getLogger("videobot")

    if cfg.webhook_url:
        # ---- webhook mode (Render free tier) ----
        log.info("Starting VideoBot in webhook mode...")
        app.run_webhook(
            listen="0.0.0.0",
            port=cfg.port,
            url_path=cfg.bot_token,  # secret path, not guessable
            webhook_url=f"{cfg.webhook_url}/{cfg.bot_token}",
            allowed_updates=["message", "callback_query"],
            bootstrap_retries=5,
        )
    else:
        # ---- polling mode (local) ----
        log.info("Starting VideoBot... (Ctrl+C to stop)")
        try:
            asyncio.run(_delete_webhook(cfg.bot_token))
        except Exception as e:  # noqa: BLE001 — startup must not die here
            log.warning("Could not delete webhook: %s", e)
        app.run_polling(
            allowed_updates=["message", "callback_query"],
            bootstrap_retries=5,  # survive transient network/proxy hiccups
        )


if __name__ == "__main__":
    main()
