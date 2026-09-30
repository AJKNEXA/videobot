# VideoBot 🎬

Telegram bot jo **protected, khud-delete hone wali videos** deta hai — referral system ke sath.

## Features

- 🎬 **Get Video** — aik button, foran video
- 🛡 **Protected content** — no forward, no save (official Telegram apps mein)
- ⏱ **Auto-delete** — 10 minute baad video khud delete (configurable)
- 📺 **Daily limit** — roz 5 free videos (configurable)
- 👥 **Referral unlock** — 3 dost invite karo → 🔓 unlimited videos
- 🛠 **Admin panel** — video add/list/delete, stats
- 💾 SQLite — koi alag database server nahi chahiye

## Limitations (honest)

- ❌ **Screenshot block nahi ho sakta** — Telegram Bot API mein ye feature nahi hai. Koi bhi bot ye claim kare to jhoot hai.
- Bot restart hone par pending auto-deletes zaya ho jati hain (video reh jayegi).

## Setup

```bash
cd videobot
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # agar ho to, warna env vars set karein
BOT_TOKEN='<token>' ADMIN_IDS='<your_id>' .venv/bin/python bot.py
```

## Files

- `bot.py` — entry point
- `config.py` — env config
- `db.py` — SQLite layer
- `handlers.py` — sari logic
- `keyboards.py` — buttons
- `texts.py` — English UI strings
- `test_videobot.py` — 37 assertions
