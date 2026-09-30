# VideoBot — Free 24/7 Deploy Guide (Render)

Ye guide bot ko **Render.com ke free plan** par hamesha online rakhegi.
Koi credit card nahi chahiye. Kul kharcha: **Rs. 0**.

Chahiye hoga: GitHub account, Supabase account, Render account, UptimeRobot
account — charon free, sirf email se bante hain.

---

## Step 1 — Code GitHub par dalo

1. [github.com](https://github.com) par account banao (agar nahi hai).
2. **New repository** → naam `videobot` → **Public** → Create.
3. Is zip ko apne phone/PC par extract karo, phir repository page par
   **Add file → Upload files** → saari files drag-drop karke **Commit**.
   (`.venv`, `__pycache__`, `.db` files upload mat karna — zip mein ye
   pehle se nikli hui hain.)

## Step 2 — Free Postgres database (Supabase)

Render ke free plan par files restart par delete ho jati hain, is liye
users/videos ka data **Postgres** mein rahega (bot khud ye sambhalta hai).

1. [supabase.com](https://supabase.com) par free account banao.
2. **New project** → koi naam do → database password set karo (likh lo!) →
   Create (2-3 min lagte hain).
3. Project khulne ke baad: **Settings (⚙️) → Database** → neeche
   **Connection string → URI** copy karo.
4. Us string mein `[YOUR-PASSWORD]` ki jagah apna password likh do.
   Ye tumhara `DATABASE_URL` hai — sambhal kar rakho.

## Step 3 — Render par bot deploy karo

1. [render.com](https://render.com) par **GitHub se sign up** karo.
2. Dashboard → **New → Blueprint** → apni `videobot` repository connect karo
   (render.yaml khud parh liya jayega).
3. **Apply** dabao. Jab environment variables mange to ye dalo:

   | Key | Value |
   |---|---|
   | `BOT_TOKEN` | BotFather se naya token (@BotFather → /mybots → API Token → revoke karke naya lo, purana expose ho chuka tha) |
   | `ADMIN_IDS` | `7354864176` |
   | `DATABASE_URL` | Step 2 wali connection string |
   | `WEBHOOK_URL` | *pehle khali chhoro* |

4. Deploy complete hone do (5-10 min). Service ka URL milega, jaise
   `https://videobot-abcd.onrender.com` — copy karo.
5. Ab service → **Environment** → `WEBHOOK_URL` mein ye URL dal kar **Save**.
   Dobara deploy hoga — ab bot **webhook mode** mein chalega. ✅

## Step 4 — Bot ko sone se roko (UptimeRobot)

Render free services 15 min khali rehne par so jati hain. Is se bachne ke
liye har 5 min mein aik ping jayegi:

1. [uptimerobot.com](https://uptimerobot.com) par free account banao.
2. **Add Monitor** → Type **HTTP(s)** → URL mein apna Render URL dalo
   (`https://videobot-abcd.onrender.com/`) → Interval **5 minutes** → Create.

Bas! Ab bot 24/7 online rahega.

## Step 5 — Test karo

Telegram par bot ko `/start` bhejo. Phir `/admin` → videos add karo,
broadcast try karo. Sab kuch pehle jaisa kaam karega.

---

## Zaroori baatein

- **Token kabhi code/GitHub mein mat likho** — sirf Render ke Environment
  variables mein. GitHub repo public hai.
- Render par har **nayi deploy** par bot 1-2 min restart hota hai — normal hai.
- Free plan mein mahine ke **750 hours** miltay hain = 1 service pooray
  mahine 24/7 ke liye kaafi hai.
- Agar kabhi paid lena ho to Render ka Starter ($7/month) "sone" wala masla
  hamesha ke liye khatam kar deta hai — lekin free wala setup bhi theek
  chalta hai.
