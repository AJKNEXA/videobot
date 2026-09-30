# VideoBot — USAGE.md

## User ke liye

1. Bot ko Telegram mein kholein aur **/start** dabayein.
2. **🎬 Get Video** button dabayein — video foran mil jayegi.
3. Video **forward nahi** ho sakti, **save nahi** ho sakti, aur **10 minute baad khud delete** ho jayegi.
4. Rozana **5 videos free** hain. Limit khatam ho jaye to apna **invite link** doston ko bhejein — **3 dost** join kar lein to **unlimited videos** unlock! 🔓

> ⚠️ Note: Screenshot ko koi bhi Telegram bot block nahi kar sakta — ye Telegram ki limit hai, bot ki nahi.

## Admin ke liye (`/admin`)

Sirf `ADMIN_IDS` mein shamil IDs ke liye kaam karta hai.

- **➕ Add Video** — apni gallery se video bhej dein (ya forward kar dein). Bot usay save kar lega, dobara upload nahi karna parta.
- **🎬 Videos** — sari videos ki list; 🗑 dabakar delete karein.
- **📊 Stats** — total users, videos, aaj ke views, total views.
- **📢 Broadcast** — sab users ko message bhejo (text ya photo). Optional link button: `Button Text | https://t.me/xyz` ya /skip. Preview ke baad ✅ Send se sab ko jayega, report milegi (sent/failed).

## Settings (`.env`)

| Variable | Default | Matlab |
|---|---|---|
| `BOT_TOKEN` | — | BotFather se mila token (zaroori) |
| `ADMIN_IDS` | — | Admin Telegram IDs, comma se alag (zaroori) |
| `DAILY_LIMIT` | 5 | Rozana free videos per user |
| `REFERRALS_NEEDED` | 3 | Unlimited ke liye kitne referrals |
| `DELETE_AFTER` | 600 | Video kitne seconds baad delete ho (600 = 10 min) |
| `DB_PATH` | videobot.db | Database file |

## Chalana

```bash
pip install -r requirements.txt
BOT_TOKEN='...' ADMIN_IDS='...' python bot.py
```
