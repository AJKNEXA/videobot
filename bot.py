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


def _build_web_app(ptb_app, cfg):
    """aiohttp app serving Telegram updates + a public /health endpoint.

    Routes:
    - POST /<bot_token>  — Telegram update delivery (secret path)
    - GET  /health       — public liveness probe (UptimeRobot etc.)
    """
    from aiohttp import web
    from telegram import Update

    async def telegram_hook(request):
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001 — not JSON, not from Telegram
            return web.Response(status=400)
        try:
            update = Update.de_json(data, ptb_app.bot)
            if update is not None:
                await ptb_app.process_update(update)
        except Exception:  # noqa: BLE001 — acknowledge to avoid retry storms
            logging.getLogger("videobot").exception(
                "Error processing webhook update")
        return web.Response(status=200)

    async def health(_request):
        return web.json_response({"ok": True, "service": "videobot"})

    web_app = web.Application()
    web_app.router.add_post(f"/{cfg.bot_token}", telegram_hook)
    web_app.router.add_get("/health", health)
    return web_app


def _run_webhook(ptb_app, cfg) -> None:
    """Blocking webhook server: Telegram POSTs + GET /health on one port."""
    import asyncio as _asyncio

    from aiohttp import web

    log = logging.getLogger("videobot")
    web_app = _build_web_app(ptb_app, cfg)

    async def on_startup(_web_app):
        await ptb_app.initialize()
        await ptb_app.start()
        # retry set_webhook through transient network hiccups
        for attempt in range(5):
            try:
                await ptb_app.bot.set_webhook(
                    url=f"{cfg.webhook_url}/{cfg.bot_token}",
                    allowed_updates=["message", "callback_query"],
                    max_connections=40,
                )
                break
            except Exception as e:  # noqa: BLE001
                log.warning("set_webhook attempt %d failed: %s",
                            attempt + 1, e)
                await _asyncio.sleep(2 * (attempt + 1))
        log.info("Webhook serving on port %d", cfg.port)

    async def on_cleanup(_web_app):
        await ptb_app.stop()
        await ptb_app.shutdown()

    web_app.on_startup.append(on_startup)
    web_app.on_cleanup.append(on_cleanup)
    web.run_app(web_app, host="0.0.0.0", port=cfg.port, print=None)


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
        _run_webhook(app, cfg)
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
