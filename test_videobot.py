#!/usr/bin/env python3
"""Tests for VideoBot: db layer + handler logic with fake Telegram objects."""
import asyncio
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["ADMIN_IDS"] = "999"
import handlers  # noqa: E402
import keyboards  # noqa: E402
from config import Config  # noqa: E402
from db import Database  # noqa: E402

PASS = []


def check(name, cond):
    assert cond, f"FAILED: {name}"
    PASS.append(name)


class FakeUser:
    def __init__(self, uid, username="u", first_name="U"):
        self.id = uid
        self.username = username
        self.first_name = first_name


class FakeVideo:
    def __init__(self):
        self.file_id = "FILEID123"
        self.file_unique_id = "UNIQUE123"
        self.duration = 42


class FakeMessage:
    def __init__(self, text="", chat_id=1, video=None):
        self.text = text
        self.chat_id = chat_id
        self.chat = MagicMock()
        self.chat.id = chat_id
        self.video = video
        self.photo = None
        self.caption = None
        self.reply_html = AsyncMock()
        self.reply_text = AsyncMock()
        self.reply_photo = AsyncMock()


class FakeCQ:
    def __init__(self, data, user, chat_id=1):
        self.data = data
        self.from_user = user
        self.answer = AsyncMock()
        self.edit_message_text = AsyncMock()
        self.message = FakeMessage(chat_id=chat_id)


class FakeUpdate:
    def __init__(self, user, message=None, cq=None):
        self.effective_user = user
        self.message = message
        self.callback_query = cq


class FakeBot:
    def __init__(self):
        self.username = "testvideobot"
        self.send_video = AsyncMock()
        self.delete_message = AsyncMock()
        self.send_message = AsyncMock()
        self.send_photo = AsyncMock()


class FakeContext:
    def __init__(self, bot, db, cfg):
        self.bot = bot
        self.bot_data = {"db": db, "cfg": cfg}
        self.user_data = {}
        self.args = []


def msg_update(user, text="", video=None):
    return FakeUpdate(user, message=FakeMessage(text, video=video))


def cq_update(user, data):
    return FakeUpdate(user, cq=FakeCQ(data, user))


async def main():
    tmp = tempfile.mkdtemp()
    db = Database(os.path.join(tmp, "t.db"))
    cfg = Config()
    cfg.admin_ids = (999,)
    cfg.daily_limit = 5
    cfg.referrals_needed = 3
    cfg.delete_after = 0  # instant delete in tests
    bot = FakeBot()
    admin = FakeUser(999, "admin", "Admin")

    def ctx_for():
        return FakeContext(bot, db, cfg)

    # ---- db: users & referrals ----
    is_new, _ = db.get_or_create_user(111, "alice", None)
    check("user created", is_new)
    is_new2, _ = db.get_or_create_user(111, "alice", None)
    check("user not new twice", not is_new2)
    db.get_or_create_user(222, "bob", 111)
    db.get_or_create_user(333, "cara", 111)
    check("referral count 2", db.count_referrals(111) == 2)
    check("no self-referral counted", db.count_referrals(222) == 0)

    # ---- db: videos ----
    check("no videos initially", db.count_videos() == 0)
    check("random none when empty", db.random_video() is None)
    vid = db.add_video("FID1", "U1", 10, 999)
    check("video added", vid is not None)
    check("duplicate rejected", db.add_video("FID1", "U1", 10, 999) is None)
    db.add_video("FID2", "U2", 20, 999)
    check("two videos", db.count_videos() == 2)
    check("random returns one", db.random_video()["id"] in (1, 2))
    check("delete works", db.delete_video(1))
    check("one left", db.count_videos() == 1)
    check("delete missing false", not db.delete_video(999))

    # ---- unseen-video logic (no repeats) ----
    db.add_video("FID3", "U3", 30, 999)
    db.add_video("FID4", "U4", 40, 999)
    v = db.random_unseen_video(112)
    check("unseen video served", v is not None)
    db.log_view(112, v["id"])
    v2 = db.random_unseen_video(112)
    check("no repeat while unseen remain", v2["id"] != v["id"])
    # mark all seen -> falls back to random
    for vv in db.list_videos():
        db.log_view(112, vv["id"])
    check("fallback when all seen",
          db.random_unseen_video(112) is not None)

    # ---- db: views ----
    check("no views today", db.today_views(111) == 0)
    db.log_view(111, 2)
    db.log_view(111, 2)
    check("two views logged", db.today_views(111) == 2)

    # ---- start with referral ----
    newbie = FakeUser(444, "dave", "Dave")
    await handlers.start(msg_update(newbie, "/start ref_111"), ctx_for())
    u = db.get_user(444)
    check("referred_by set", u["referred_by"] == 111)
    check("referral count 3", db.count_referrals(111) == 3)
    # welcome message contains invite link
    # re-run capturing reply
    ctx = ctx_for()
    upd = msg_update(newbie, "/start")
    await handlers.start(upd, ctx)
    sent = upd.message.reply_html.call_args[0][0]
    check("welcome has invite link", "ref_444" in sent)

    # bad ref ignored
    odd = FakeUser(555, "erin", "Erin")
    await handlers.start(msg_update(odd, "/start ref_999999"), ctx_for())
    check("bad ref ignored", db.get_user(555)["referred_by"] is None)
    # self ref ignored
    await handlers.start(msg_update(odd, "/start ref_555"), ctx_for())
    check("self ref ignored", db.get_user(555)["referred_by"] is None)

    # ---- get_video: under limit ----
    async def sent_video():
        m = MagicMock()
        m.message_id = 77
        bot.send_video.return_value = m
        return m

    viewer = FakeUser(666, "fred", "Fred")
    q = cq_update(viewer, "get_video")
    await sent_video()
    await handlers.get_video_cb(q, ctx_for())
    check("video sent", bot.send_video.await_count == 1)
    kwargs = bot.send_video.call_args[1]
    check("protect_content on", kwargs.get("protect_content") is True)
    check("view logged", db.today_views(666) == 1)
    await asyncio.sleep(0.05)  # let auto-delete task run
    check("auto-delete called", bot.delete_message.await_count == 1)

    # ---- get_video: limit reached, no referrals ----
    for _ in range(4):
        await handlers.get_video_cb(cq_update(viewer, "get_video"), ctx_for())
    check("5 views total", db.today_views(666) == 5)
    q = cq_update(viewer, "get_video")
    before = bot.send_video.await_count
    await handlers.get_video_cb(q, ctx_for())
    check("6th blocked", bot.send_video.await_count == before)
    check("limit msg sent",
          "Daily limit reached" in q.callback_query.message.reply_html.call_args[0][0])

    # ---- get_video: unlocked via 3 referrals ----
    ref_user = FakeUser(777, "gina", "Gina")
    await handlers.start(msg_update(ref_user, "/start"), ctx_for())
    for i in range(3):
        r = FakeUser(800 + i, f"r{i}", f"R{i}")
        await handlers.start(msg_update(r, "/start ref_777"), ctx_for())
    check("3 referrals", db.count_referrals(777) == 3)
    for _ in range(7):
        await handlers.get_video_cb(cq_update(ref_user, "get_video"), ctx_for())
    check("unlimited after 3 refs", db.today_views(777) == 7)

    # ---- get_video: no videos ----
    db2 = Database(os.path.join(tmp, "t2.db"))
    ctx2 = FakeContext(bot, db2, cfg)
    q = cq_update(viewer, "get_video")
    await handlers.get_video_cb(q, ctx2)
    q.callback_query.answer.assert_called()

    # ---- admin: denied for non-admin ----
    await handlers.admin_cmd(msg_update(viewer, "/admin"), ctx_for())
    # (just shouldn't crash; covered by reply mock)

    # ---- admin: add video conversation ----
    c = ctx_for()
    n_before = db.count_videos()
    q = cq_update(admin, "admin:addvideo")
    st = await handlers.addvideo_start(q, c)
    check("addvideo -> ADD_VIDEO", st == handlers.ADD_VIDEO)
    st = await handlers.addvideo_received(
        msg_update(admin, video=FakeVideo()), c)
    check("video saved -> END", st == handlers.ConversationHandler.END)
    check("video in db", db.count_videos() == n_before + 1)

    # non-admin addvideo denied
    c = ctx_for()
    q = cq_update(viewer, "admin:addvideo")
    st = await handlers.addvideo_start(q, c)
    check("non-admin denied", st == handlers.ConversationHandler.END)

    # ---- admin: videos list + delete + stats ----
    q = cq_update(admin, "admin:videos")
    await handlers.admin_cb(q, ctx_for())
    check("videos panel",
          "Video Library" in q.callback_query.edit_message_text.call_args[0][0])
    q = cq_update(admin, "admin:del:2")
    n_before = db.count_videos()
    await handlers.admin_cb(q, ctx_for())
    check("video deleted via panel", db.count_videos() == n_before - 1)
    q = cq_update(admin, "admin:stats")
    await handlers.admin_cb(q, ctx_for())
    check("stats shown",
          "Stats" in q.callback_query.edit_message_text.call_args[0][0])

    # main menu has single Get Video button + invite
    kb = keyboards.main_menu("https://t.me/share/url?url=x")
    labels = [b.text for row in kb.inline_keyboard for b in row]
    check("Get Video button", any("Get Video" in l for l in labels))

    # ---- bottom keyboard ----
    from telegram import ReplyKeyboardMarkup
    kb = keyboards.bottom_menu()
    check("bottom menu is reply keyboard",
          isinstance(kb, ReplyKeyboardMarkup))
    blabels = [b.text for row in kb.keyboard for b in row]
    check("bottom has Get Video", "🎬 Get Video" in blabels)
    check("bottom has Invite Friends", "👥 Invite Friends" in blabels)

    buser = FakeUser(900, "ivan", "Ivan")
    upd = msg_update(buser, "/start")
    await handlers.start(upd, ctx_for())
    check("start sends bottom menu",
          isinstance(upd.message.reply_html.call_args[1]["reply_markup"],
                     ReplyKeyboardMarkup))

    before = bot.send_video.await_count
    await handlers.bottom_text(msg_update(buser, "🎬 Get Video"), ctx_for())
    check("bottom Get Video serves",
          bot.send_video.await_count == before + 1)
    check("bottom Get Video logged", db.today_views(900) == 1)

    upd = msg_update(buser, "👥 Invite Friends")
    await handlers.bottom_text(upd, ctx_for())
    check("invite card sent",
          "ref_900" in upd.message.reply_html.call_args[0][0])

    # ---- broadcast ----
    q = cq_update(admin, "admin:broadcast")
    st = await handlers.broadcast_start(q, ctx_for())
    check("broadcast start -> MSG", st == handlers.BROADCAST_MSG)
    check("broadcast asks for message",
          "Broadcast" in q.callback_query.edit_message_text.call_args[0][0])

    qx = cq_update(FakeUser(123, "x", "X"), "admin:broadcast")
    st = await handlers.broadcast_start(qx, ctx_for())
    check("broadcast non-admin denied",
          st == handlers.ConversationHandler.END)

    c = ctx_for()
    st = await handlers.broadcast_msg_received(msg_update(admin, "Hello all!"), c)
    check("broadcast msg -> LINK", st == handlers.BROADCAST_LINK)
    check("draft text stored",
          c.user_data["broadcast"]["text"] == "Hello all!")

    st = await handlers.broadcast_link_received(
        msg_update(admin, "Join Channel | https://t.me/boosteleofficial"), c)
    check("broadcast link -> CONFIRM", st == handlers.BROADCAST_CONFIRM)
    d = c.user_data["broadcast"]
    check("link label parsed", d["label"] == "Join Channel")
    check("link url parsed", d["url"] == "https://t.me/boosteleofficial")

    c2 = ctx_for()
    await handlers.broadcast_msg_received(msg_update(admin, "Hi"), c2)
    st = await handlers.broadcast_link_received(
        msg_update(admin, "badformat-no-pipe"), c2)
    check("bad link stays in LINK", st == handlers.BROADCAST_LINK)

    c3 = ctx_for()
    await handlers.broadcast_msg_received(msg_update(admin, "Hi again"), c3)
    st = await handlers.broadcast_skip_link(msg_update(admin, "/skip"), c3)
    check("skip link -> CONFIRM", st == handlers.BROADCAST_CONFIRM)
    check("no url after skip", "url" not in c3.user_data["broadcast"])

    check("all_user_ids works", len(db.all_user_ids()) > 0)
    c4 = ctx_for()
    await handlers.broadcast_msg_received(msg_update(admin, "Final msg"), c4)
    q2 = cq_update(admin, "broadcast:send")
    st = await handlers.broadcast_confirm_cb(q2, c4)
    check("broadcast send -> END", st == handlers.ConversationHandler.END)
    n_users = len(db.all_user_ids())
    check("sent to all users", bot.send_message.await_count == n_users)
    check("done report shown",
          "Broadcast done" in
          q2.callback_query.message.reply_html.call_args[0][0])

    q5 = cq_update(admin, "broadcast:cancel")
    c5 = ctx_for()
    c5.user_data["broadcast"] = {"text": "x"}
    st = await handlers.broadcast_confirm_cb(q5, c5)
    check("broadcast cancel -> END", st == handlers.ConversationHandler.END)
    check("draft cleared on cancel", "broadcast" not in c5.user_data)

    print(f"\nALL {len(PASS)} VIDEOBOT ASSERTIONS PASSED")


asyncio.run(main())
