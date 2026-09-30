"""Inline keyboards for VideoBot."""
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def bottom_menu() -> ReplyKeyboardMarkup:
    """Persistent bottom keyboard: Get Video + Invite Friends."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🎬 Get Video")],
         [KeyboardButton("👥 Invite Friends")]],
        resize_keyboard=True,
    )


def main_menu(share_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Get Video", callback_data="get_video")],
        [InlineKeyboardButton("👥 Invite Friends", url=share_url)],
    ])


def invite_only(share_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Invite Friends", url=share_url)],
    ])


def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Video", callback_data="admin:addvideo")],
        [InlineKeyboardButton("🎬 Videos", callback_data="admin:videos"),
         InlineKeyboardButton("📊 Stats", callback_data="admin:stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast")],
    ])


def videos_list(videos: list) -> InlineKeyboardMarkup:
    import texts as T
    rows = []
    for v in videos:
        rows.append([InlineKeyboardButton(
            f"🗑 {T.video_row(v)}",
            callback_data=f"admin:del:{v['id']}")])
    rows.append([InlineKeyboardButton("⬅️ Admin Panel",
                                      callback_data="admin:panel")])
    return InlineKeyboardMarkup(rows)
