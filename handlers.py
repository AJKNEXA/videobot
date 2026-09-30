"""Handlers for VideoBot: disappearing protected videos + referrals."""
import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import keyboards
import texts as T
from config import Config
from db import Database

log = logging.getLogger("videobot")

ADD_VIDEO = 1
BROADCAST_MSG, BROADCAST_LINK, BROADCAST_CONFIRM = 2, 3, 4


def _db(context) -> Database:
    return context.bot_data["db"]


def _cfg(context) -> Config:
    return context.bot_data["cfg"]


def _is_admin(uid: int, cfg: Config) -> bool:
    return uid in cfg.admin_ids


def _invite_link(context, uid: int) -> str:
    return f"https://t.me/{context.bot.username}?start=ref_{uid}"


def _share_link(context, uid: int) -> str:
    from urllib.parse import quote
    link = _invite_link(context, uid)
    text = quote("Watch exclusive videos here! 🎬")
    return f"https://t.me/share/url?url={quote(link)}&text={text}"


def _parse_ref(text: str | None) -> int | None:
    parts = (text or "").split()
    if len(parts) >= 2 and parts[1].startswith("ref_"):
        try:
            return int(parts[1][4:])
        except ValueError:
            return None
    return None


def _status_line(db: Database, cfg: Config, uid: int) -> str:
    refs = db.count_referrals(uid)
    if refs >= cfg.referrals_needed:
        return T.status_unlimited(refs)
    views = db.today_views(uid)
    return T.status_limited(views, cfg.daily_limit, refs, cfg.referrals_needed)


# ============================== user ==============================
async def _notify_referrer(context, ref_id: int, db: Database,
                         cfg: Config) -> None:
    """Tell the referrer someone joined via their link (best-effort)."""
    refs = db.count_referrals(ref_id)
    try:
        await context.bot.send_message(
            chat_id=ref_id,
            text=T.referral_joined(refs, cfg.referrals_needed),
            parse_mode="HTML",
        )
    except TelegramError:
        log.warning("Could not notify referrer %s of new join", ref_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = _db(context)
    ref = _parse_ref(update.message.text if update.message else None)
    if ref == user.id:
        ref = None
    if ref and not db.get_user(ref):
        ref = None
    is_new, _ = db.get_or_create_user(user.id, user.username, ref)
    if is_new and ref:
        # genuine new join via someone's link — notify the referrer
        await _notify_referrer(context, ref, db, _cfg(context))
    await update.message.reply_html(
        T.welcome(user.first_name,
                  _status_line(db, _cfg(context), user.id),
                  _invite_link(context, user.id)),
        reply_markup=keyboards.bottom_menu(),
    )


async def _auto_delete(bot, chat_id: int, message_id: int, delay: int):
    """Delete the video message after `delay` seconds."""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramError:
        pass


async def _serve_video_request(context, uid: int, username: str | None,
                             chat_id: int, send_text):
    """Shared Get-Video logic for inline button AND bottom keyboard.

    send_text: async callable like message.reply_html(text, reply_markup=...).
    """
    db, cfg = _db(context), _cfg(context)
    db.get_or_create_user(uid, username, None)

    if db.count_videos() == 0:
        await send_text(T.NO_VIDEOS)
        return

    views = db.today_views(uid)
    refs = db.count_referrals(uid)
    unlocked = refs >= cfg.referrals_needed

    if views >= cfg.daily_limit and not unlocked:
        await send_text(
            T.limit_reached(views, refs, cfg.referrals_needed,
                            _invite_link(context, uid)),
            reply_markup=keyboards.invite_only(_share_link(context, uid)),
        )
        return

    vid = db.random_unseen_video(uid)
    if not vid:
        await send_text(T.NO_VIDEOS)
        return
    db.log_view(uid, vid["id"])
    views_after = db.today_views(uid)
    msg = await context.bot.send_video(
        chat_id=chat_id,
        video=vid["file_id"],
        protect_content=True,  # no forward, no save
        caption=T.video_caption(views_after, cfg.daily_limit, unlocked, refs),
    )
    asyncio.create_task(
        _auto_delete(context.bot, chat_id, msg.message_id, cfg.delete_after)
    )


async def get_video_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    async def send_text(text, reply_markup=None):
        await q.message.reply_html(text, reply_markup=reply_markup)

    await _serve_video_request(context, q.from_user.id,
                               q.from_user.username,
                               q.message.chat_id, send_text)


async def bottom_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Persistent bottom keyboard presses."""
    text = (update.message.text or "").strip()
    user = update.effective_user
    if text == "🎬 Get Video":
        await _serve_video_request(context, user.id, user.username,
                                   update.message.chat_id,
                                   update.message.reply_html)
    elif text == "👥 Invite Friends":
        db, cfg = _db(context), _cfg(context)
        refs = db.count_referrals(user.id)
        await update.message.reply_html(
            T.invite_card(_invite_link(context, user.id),
                          refs, cfg.referrals_needed),
            reply_markup=keyboards.invite_only(_share_link(context, user.id)),
        )


# ============================== admin ==============================
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id, _cfg(context)):
        await update.message.reply_html(T.ADMIN_DENIED)
        return
    await update.message.reply_html(
        T.ADMIN_PANEL, reply_markup=keyboards.admin_panel())


async def admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    db = _db(context)
    if not _is_admin(q.from_user.id, _cfg(context)):
        await q.edit_message_text(T.ADMIN_DENIED)
        return
    action = q.data.split(":", 1)[1]

    if action == "panel":
        await q.edit_message_text(T.ADMIN_PANEL, parse_mode="HTML",
                                  reply_markup=keyboards.admin_panel())
    elif action == "stats":
        await q.edit_message_text(T.stats_text(db.stats()), parse_mode="HTML",
                                  reply_markup=keyboards.admin_panel())
    elif action == "videos":
        vids = db.list_videos()
        text = T.VIDEOS_HEAD if vids else T.VIDEOS_EMPTY
        await q.edit_message_text(text, parse_mode="HTML",
                                  reply_markup=keyboards.videos_list(vids))
    elif action.startswith("del:"):
        try:
            vid_id = int(action.split(":")[1])
        except (ValueError, IndexError):
            return
        db.delete_video(vid_id)
        vids = db.list_videos()
        text = T.VIDEO_DELETED + "\n\n" + (
            T.VIDEOS_HEAD if vids else T.VIDEOS_EMPTY)
        await q.edit_message_text(text, parse_mode="HTML",
                                  reply_markup=keyboards.videos_list(vids))


async def addvideo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _is_admin(q.from_user.id, _cfg(context)):
        await q.edit_message_text(T.ADMIN_DENIED)
        return ConversationHandler.END
    await q.edit_message_text(T.ASK_VIDEO, parse_mode="HTML")
    return ADD_VIDEO


async def addvideo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = _db(context)
    v = update.message.video
    vid_id = db.add_video(v.file_id, v.file_unique_id, v.duration or 0,
                          update.effective_user.id)
    if vid_id is None:
        await update.message.reply_html(T.VIDEO_DUP)
    else:
        await update.message.reply_html(
            T.VIDEO_ADDED, reply_markup=keyboards.admin_panel())
    return ConversationHandler.END


async def conv_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        T.ADMIN_PANEL, reply_markup=keyboards.admin_panel())
    return ConversationHandler.END


# ============================== broadcast ==============================
def _broadcast_kb(draft: dict):
    """Inline keyboard with the optional link button."""
    if draft.get("url"):
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(draft["label"], url=draft["url"])
        ]])
    return None


async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _is_admin(q.from_user.id, _cfg(context)):
        await q.edit_message_text(T.ADMIN_DENIED)
        return ConversationHandler.END
    context.user_data["broadcast"] = {}
    await q.edit_message_text(T.BROADCAST_ASK_MSG, parse_mode="HTML")
    return BROADCAST_MSG


async def broadcast_msg_received(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data.setdefault("broadcast", {})
    msg = update.message
    if msg.photo:
        draft["kind"] = "photo"
        draft["file_id"] = msg.photo[-1].file_id
        draft["caption"] = msg.caption or ""
    else:
        draft["kind"] = "text"
        draft["text"] = msg.text
    await msg.reply_html(T.BROADCAST_ASK_LINK, parse_mode="HTML")
    return BROADCAST_LINK


async def broadcast_skip_link(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    return await _broadcast_preview(update, context)


async def broadcast_link_received(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or "").strip()
    if "|" not in raw:
        await update.message.reply_html(T.BROADCAST_BAD_LINK,
                                        parse_mode="HTML")
        return BROADCAST_LINK
    label, url = [p.strip() for p in raw.split("|", 1)]
    if not label or not url:
        await update.message.reply_html(T.BROADCAST_BAD_LINK,
                                        parse_mode="HTML")
        return BROADCAST_LINK
    if not url.startswith(("http://", "https://")):
        url = "https://" + url.lstrip("/")
    draft = context.user_data.setdefault("broadcast", {})
    draft["label"] = label
    draft["url"] = url
    return await _broadcast_preview(update, context)


async def _broadcast_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data.get("broadcast", {})
    msg = update.message
    kb = _broadcast_kb(draft)
    if draft.get("kind") == "photo":
        await msg.reply_photo(draft["file_id"],
                              caption=draft.get("caption") or None,
                              parse_mode="HTML", reply_markup=kb)
    else:
        await msg.reply_html(draft.get("text", ""), reply_markup=kb)
    n = len(_db(context).all_user_ids())
    await msg.reply_html(
        T.broadcast_confirm(n),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Send", callback_data="broadcast:send"),
            InlineKeyboardButton("❌ Cancel", callback_data="broadcast:cancel"),
        ]]),
    )
    return BROADCAST_CONFIRM


async def broadcast_confirm_cb(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "broadcast:cancel":
        context.user_data.pop("broadcast", None)
        await q.edit_message_text(T.BROADCAST_CANCELLED)
        return ConversationHandler.END

    draft = context.user_data.pop("broadcast", {})
    await q.edit_message_text(T.BROADCAST_SENDING)
    db = _db(context)
    kb = _broadcast_kb(draft)
    ok = fail = 0
    for uid in db.all_user_ids():
        try:
            if draft.get("kind") == "photo":
                await context.bot.send_photo(
                    uid, draft["file_id"],
                    caption=draft.get("caption") or None,
                    parse_mode="HTML", reply_markup=kb)
            else:
                await context.bot.send_message(
                    uid, draft.get("text", ""),
                    parse_mode="HTML", reply_markup=kb)
            ok += 1
        except TelegramError:
            fail += 1
        await asyncio.sleep(0.05)
    await q.message.reply_html(T.broadcast_done(ok, fail),
                               reply_markup=keyboards.admin_panel())
    return ConversationHandler.END


# ============================== wiring ==============================
def register(app: Application) -> None:
    # 1) add-video conversation (before the generic admin: handler)
    addvid_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(addvideo_start,
                                           pattern=r"^admin:addvideo$")],
        states={
            ADD_VIDEO: [MessageHandler(filters.VIDEO & ~filters.COMMAND,
                                       addvideo_received)],
        },
        fallbacks=[CommandHandler("cancel", conv_cancel)],
        per_message=False,
    )
    app.add_handler(addvid_conv)

    # 1b) broadcast conversation
    bcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(broadcast_start,
                                           pattern=r"^admin:broadcast$")],
        states={
            BROADCAST_MSG: [MessageHandler(
                filters.PHOTO | (filters.TEXT & ~filters.COMMAND),
                broadcast_msg_received)],
            BROADCAST_LINK: [
                CommandHandler("skip", broadcast_skip_link),
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               broadcast_link_received),
            ],
            BROADCAST_CONFIRM: [CallbackQueryHandler(
                broadcast_confirm_cb, pattern=r"^broadcast:(send|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", conv_cancel)],
        per_message=False,
    )
    app.add_handler(bcast_conv)

    # 2) commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))

    # 3) callbacks
    app.add_handler(CallbackQueryHandler(get_video_cb,
                                         pattern=r"^get_video$"))
    app.add_handler(CallbackQueryHandler(admin_cb, pattern=r"^admin:"))

    # 4) persistent bottom keyboard (after conversations so /cancel etc. win)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                   bottom_text))
