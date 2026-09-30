"""Database layer for VideoBot.

Two backends, same API:
- SQLite (stdlib) — default, local dev / testing.
- PostgreSQL (psycopg3) — when a DSN is given (DATABASE_URL on Render).

Queries are written once with `?` placeholders and translated to `%s`
for Postgres. Date filters use the backend-appropriate "today" expression
(Postgres connection runs in Asia/Karachi so CURRENT_DATE == user's day).
"""
import threading

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS users(
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    referred_by INTEGER,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS videos(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id        TEXT NOT NULL,
    file_unique_id TEXT NOT NULL UNIQUE,
    duration       INTEGER NOT NULL DEFAULT 0,
    added_by       INTEGER,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS views(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    video_id   INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_views_user_day ON views(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_users_referred ON users(referred_by);
"""

SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS users(
    user_id     BIGINT PRIMARY KEY,
    username    TEXT,
    referred_by BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS videos(
    id             BIGSERIAL PRIMARY KEY,
    file_id        TEXT NOT NULL,
    file_unique_id TEXT NOT NULL UNIQUE,
    duration       INTEGER NOT NULL DEFAULT 0,
    added_by       BIGINT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS views(
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    video_id   BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_views_user_day ON views(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_users_referred ON users(referred_by);
"""

TODAY_SQLITE = "date(created_at, 'localtime') = date('now', 'localtime')"
TODAY_PG = "created_at::date = CURRENT_DATE"  # session TZ = Asia/Karachi


class Database:
    def __init__(self, path: str = "videobot.db", dsn: str | None = None) -> None:
        self._lock = threading.Lock()
        self._pg = bool(dsn)
        if self._pg:
            import psycopg
            from psycopg.rows import dict_row
            self._conn = psycopg.connect(dsn, row_factory=dict_row,
                                         autocommit=True)
            self._today = TODAY_PG
            with self._lock:
                cur = self._conn.cursor()
                try:
                    cur.execute("SET TIME ZONE 'Asia/Karachi'")
                    for stmt in SCHEMA_PG.split(";"):
                        if stmt.strip():
                            cur.execute(stmt)
                finally:
                    cur.close()
        else:
            import sqlite3
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._today = TODAY_SQLITE
            with self._lock, self._conn:
                self._conn.executescript(SCHEMA_SQLITE)

    # ---------- internal helpers ----------
    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self._pg else sql

    def _fetchone(self, sql, params=()):
        if self._pg:
            with self._lock:
                cur = self._conn.cursor()
                try:
                    cur.execute(self._sql(sql), params)
                    return cur.fetchone()
                finally:
                    cur.close()
        with self._lock:
            row = self._conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def _fetchall(self, sql, params=()):
        if self._pg:
            with self._lock:
                cur = self._conn.cursor()
                try:
                    cur.execute(self._sql(sql), params)
                    return cur.fetchall()
                finally:
                    cur.close()
        with self._lock:
            return [dict(r)
                    for r in self._conn.execute(sql, params).fetchall()]

    def _execute(self, sql, params=()) -> int:
        """Execute a write; returns affected rowcount."""
        if self._pg:
            with self._lock:
                cur = self._conn.cursor()
                try:
                    cur.execute(self._sql(sql), params)
                    return cur.rowcount
                finally:
                    cur.close()
        with self._lock, self._conn:
            cur = self._conn.execute(sql, params)
            return cur.rowcount

    # ---------- users ----------
    def get_or_create_user(self, user_id: int, username: str | None,
                           referred_by: int | None = None):
        """Returns (is_new, user_dict). referred_by is set only on creation."""
        row = self._fetchone(
            "SELECT * FROM users WHERE user_id = ?", (user_id,))
        if row:
            if username and row["username"] != username:
                self._execute(
                    "UPDATE users SET username = ? WHERE user_id = ?",
                    (username, user_id))
                row["username"] = username
            return False, row
        self._execute(
            "INSERT INTO users(user_id, username, referred_by)"
            " VALUES(?,?,?)",
            (user_id, username, referred_by))
        row = self._fetchone(
            "SELECT * FROM users WHERE user_id = ?", (user_id,))
        return True, row

    def get_user(self, user_id: int):
        return self._fetchone(
            "SELECT * FROM users WHERE user_id = ?", (user_id,))

    def count_referrals(self, user_id: int) -> int:
        row = self._fetchone(
            "SELECT COUNT(*) AS c FROM users WHERE referred_by = ?",
            (user_id,))
        return row["c"]

    # ---------- views ----------
    def log_view(self, user_id: int, video_id: int) -> None:
        self._execute(
            "INSERT INTO views(user_id, video_id) VALUES(?,?)",
            (user_id, video_id))

    def today_views(self, user_id: int) -> int:
        row = self._fetchone(
            "SELECT COUNT(*) AS c FROM views"
            " WHERE user_id = ? AND " + self._today,
            (user_id,))
        return row["c"]

    # ---------- videos ----------
    def add_video(self, file_id: str, file_unique_id: str,
                  duration: int, added_by: int | None):
        """Returns new video id, or None if this video was already added."""
        exists = self._fetchone(
            "SELECT id FROM videos WHERE file_unique_id = ?",
            (file_unique_id,))
        if exists:
            return None
        if self._pg:
            with self._lock:
                cur = self._conn.cursor()
                try:
                    cur.execute(
                        "INSERT INTO videos(file_id, file_unique_id,"
                        " duration, added_by) VALUES(%s,%s,%s,%s)"
                        " RETURNING id",
                        (file_id, file_unique_id, duration, added_by))
                    return cur.fetchone()["id"]
                finally:
                    cur.close()
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO videos(file_id, file_unique_id, duration, added_by)"
                " VALUES(?,?,?,?)",
                (file_id, file_unique_id, duration, added_by))
            return cur.lastrowid

    def list_videos(self):
        return self._fetchall("SELECT * FROM videos ORDER BY id DESC")

    def random_video(self):
        return self._fetchone(
            "SELECT * FROM videos ORDER BY RANDOM() LIMIT 1")

    def random_unseen_video(self, user_id: int):
        """Random video the user hasn't watched yet.

        Falls back to a random video only when the user has seen them all.
        """
        row = self._fetchone(
            "SELECT * FROM videos WHERE id NOT IN "
            "(SELECT video_id FROM views WHERE user_id = ?) "
            "ORDER BY RANDOM() LIMIT 1",
            (user_id,))
        if row:
            return row
        return self._fetchone(
            "SELECT * FROM videos ORDER BY RANDOM() LIMIT 1")

    def delete_video(self, video_id: int) -> bool:
        return self._execute(
            "DELETE FROM videos WHERE id = ?", (video_id,)) > 0

    def count_videos(self) -> int:
        return self._fetchone(
            "SELECT COUNT(*) AS c FROM videos")["c"]

    def all_user_ids(self):
        rows = self._fetchall("SELECT user_id FROM users ORDER BY user_id")
        return [r["user_id"] for r in rows]

    # ---------- stats ----------
    def stats(self):
        users = self._fetchone("SELECT COUNT(*) AS c FROM users")["c"]
        videos = self._fetchone("SELECT COUNT(*) AS c FROM videos")["c"]
        views_today = self._fetchone(
            "SELECT COUNT(*) AS c FROM views WHERE " + self._today)["c"]
        views_total = self._fetchone(
            "SELECT COUNT(*) AS c FROM views")["c"]
        return {"users": users, "videos": videos,
                "views_today": views_today, "views_total": views_total}
