"""All user-facing strings (English)."""


def welcome(name: str, status: str, link: str) -> str:
    return (
        f"🎬 <b>Hey {name}, welcome to Video Provider!</b>\n\n"
        f"Tap the button below to get a video —\n"
        f"always a fresh one, no repeats until you've seen them all! 👀\n"
        f"⚠️ Videos can't be forwarded or saved,\n"
        f"and they disappear after 10 minutes.\n\n"
        f"{status}\n\n"
        f"👥 <b>Your invite link:</b>\n<code>{link}</code>"
    )


def status_limited(views: int, limit: int, refs: int, needed: int) -> str:
    return (
        f"📺 Today's videos: <b>{views}/{limit}</b>\n"
        f"👥 Referrals: <b>{refs}/{needed}</b> for 🔓 unlimited videos"
    )


def status_unlimited(refs: int) -> str:
    return (
        f"🔓 <b>Unlimited videos unlocked!</b>\n"
        f"👥 Your referrals: <b>{refs}</b>"
    )


def limit_reached(views: int, refs: int, needed: int, link: str) -> str:
    more = needed - refs
    return (
        f"🚫 <b>Daily limit reached!</b>\n\n"
        f"You've watched {views} videos today.\n"
        f"👥 Referrals: <b>{refs}/{needed}</b>\n\n"
        f"Invite <b>{more}</b> more friend{'s' if more != 1 else ''} to unlock "
        f"🔓 <b>unlimited</b> videos!\n\n"
        f"👥 <b>Your invite link:</b>\n<code>{link}</code>"
    )


def video_caption(views: int, limit: int, unlocked: bool, refs: int) -> str:
    if unlocked:
        return f"🎬 Enjoy! 🔓 Unlimited (👥 {refs} referrals)"
    return f"🎬 Enjoy! 📺 {views}/{limit} videos watched today"


NO_VIDEOS = "😔 No videos available yet. Please check back later!"


def invite_card(link: str, refs: int, needed: int) -> str:
    return (
        f"👥 <b>Invite friends & unlock unlimited videos!</b>\n\n"
        f"Your referrals: <b>{refs}/{needed}</b>\n\n"
        f"Share your personal link:\n<code>{link}</code>"
    )


def referral_joined(refs: int, needed: int) -> str:
    """Message sent to the referrer when someone joins via their link."""
    if refs >= needed:
        extra = "🔓 <b>Unlimited videos unlocked!</b> 🎉"
    else:
        more = needed - refs
        extra = (f"Invite <b>{more}</b> more "
                 f"friend{'s' if more != 1 else ''} to unlock "
                 f"🔓 <b>unlimited</b> videos!")
    return (
        "🎉 <b>Someone joined using your referral link!</b>\n\n"
        f"👥 Your referrals: <b>{refs}/{needed}</b>\n\n"
        f"{extra}"
    )


# ------------------------------ broadcast (admin) ------------------------------
BROADCAST_ASK_MSG = (
    "📢 <b>Broadcast</b>\n\n"
    "Send the message you want to send to <b>ALL</b> users.\n"
    "Text or a photo with caption — both work.\n\n"
    "/cancel to abort."
)

BROADCAST_ASK_LINK = (
    "🔗 Now add a link button (optional).\n\n"
    "Send it in this format:\n"
    "<code>Button Text | https://t.me/yourchannel</code>\n\n"
    "Example:\n<code>Join Channel | https://t.me/boosteleofficial</code>\n\n"
    "Or send /skip for no button."
)

BROADCAST_BAD_LINK = (
    "❌ Wrong format. Send it like this:\n"
    "<code>Button Text | https://t.me/yourchannel</code>\n\n"
    "Or send /skip for no button."
)

BROADCAST_CANCELLED = "❌ Broadcast cancelled."

BROADCAST_SENDING = "⏳ Sending broadcast..."


def broadcast_confirm(n: int) -> str:
    return (
        f"👆 That's the preview.\n\n"
        f"Send it to <b>{n}</b> user(s)?"
    )


def broadcast_done(ok: int, fail: int) -> str:
    return (
        f"📢 <b>Broadcast done!</b>\n\n"
        f"✅ Sent: <b>{ok}</b>\n"
        f"❌ Failed: <b>{fail}</b>"
    )


# ---------- admin ----------
ADMIN_DENIED = "⛔ This command is for admins only."

ADMIN_PANEL = (
    "🛠 <b>Admin Panel</b>\n\n"
    "➕ <b>Add Video</b> — send me a video and I'll save it.\n"
    "🎬 <b>Videos</b> — list & delete videos.\n"
    "📊 <b>Stats</b> — users, videos, views."
)

ASK_VIDEO = (
    "📤 <b>Send me the video</b> now\n"
    "(as a normal video, not a file).\n\n"
    "Or /cancel to go back."
)

VIDEO_ADDED = "✅ Video saved! Users can now receive it. 🎬"

VIDEO_DUP = "⚠️ This video is already in the library."

VIDEOS_HEAD = "🎬 <b>Video Library</b>\n\nTap 🗑 to delete a video:"

VIDEOS_EMPTY = "📭 No videos yet. Tap ➕ Add Video to add one."

VIDEO_DELETED = "🗑 Video deleted."


def stats_text(s: dict) -> str:
    return (
        "📊 <b>Stats</b>\n\n"
        f"👥 Users: <b>{s['users']}</b>\n"
        f"🎬 Videos: <b>{s['videos']}</b>\n"
        f"👁 Views today: <b>{s['views_today']}</b>\n"
        f"👁 Total views: <b>{s['views_total']}</b>"
    )


def video_row(v: dict) -> str:
    dur = f" ({v['duration']}s)" if v["duration"] else ""
    return f"🎬 Video #{v['id']}{dur}"
