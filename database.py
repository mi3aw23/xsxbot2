import sqlite3
import json
from datetime import datetime
from config import DB_PATH, OWNER_ID

DEFAULT_PERMISSIONS = {
    "add_content": True,
    "delete_content": True,
    "view_stats": True,
    "manage_admins": False,
    "change_language": True,
    "view_viewers": True
}

OWNER_PERMISSIONS = {
    "add_content": True,
    "delete_content": True,
    "view_stats": True,
    "manage_admins": True,
    "change_language": True,
    "view_viewers": True
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            lang TEXT DEFAULT 'en',
            is_admin INTEGER DEFAULT 0,
            is_owner INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            permissions TEXT DEFAULT '{}',
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            file_id TEXT,
            file_type TEXT NOT NULL,
            raw_text TEXT,
            link_code TEXT UNIQUE NOT NULL,
            delete_after INTEGER DEFAULT 20,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            items_json TEXT DEFAULT '[]'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS content_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER NOT NULL,
            viewer_id INTEGER NOT NULL,
            viewer_name TEXT,
            viewer_username TEXT,
            viewed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES content(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            data TEXT DEFAULT '{}'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            sent_to INTEGER DEFAULT 0
        )
    """)

    # Migrations for older DBs
    for migration in [
        "ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0",
        "ALTER TABLE content ADD COLUMN items_json TEXT DEFAULT '[]'",
    ]:
        try:
            c.execute(migration)
        except Exception:
            pass

    conn.commit()
    conn.close()


# ─── Users ───────────────────────────────────────────────────────────────────

def upsert_user(user_id: int, username: str, first_name: str, last_name: str = ""):
    conn = get_conn()
    c = conn.cursor()
    is_owner = 1 if user_id == OWNER_ID else 0
    c.execute("""
        INSERT INTO users (id, username, first_name, last_name, is_owner, permissions)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            last_seen = CURRENT_TIMESTAMP
    """, (user_id, username or "", first_name or "", last_name or "", is_owner,
          json.dumps(OWNER_PERMISSIONS if is_owner else DEFAULT_PERMISSIONS)))
    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["permissions"] = json.loads(d.get("permissions") or "{}")
        return d
    return None


def get_user_by_username(username: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username.lstrip("@"),)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["permissions"] = json.loads(d.get("permissions") or "{}")
        return d
    return None


def get_all_users(limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM users ORDER BY joined_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["permissions"] = json.loads(d.get("permissions") or "{}")
        result.append(d)
    return result


def get_last_active_users(limit: int = 10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM users ORDER BY last_seen DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["permissions"] = json.loads(d.get("permissions") or "{}")
        result.append(d)
    return result


def get_active_users_last_minutes(minutes: int = 10) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE last_seen >= datetime('now', ?)",
        (f"-{minutes} minutes",)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def set_user_lang(user_id: int, lang: str):
    conn = get_conn()
    conn.execute("UPDATE users SET lang = ? WHERE id = ?", (lang, user_id))
    conn.commit()
    conn.close()


def get_user_lang(user_id: int) -> str:
    conn = get_conn()
    row = conn.execute("SELECT lang FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row["lang"] if row else "en"


def is_admin_or_owner(user_id: int) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT is_admin, is_owner FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return False
    return bool(row["is_admin"] or row["is_owner"])


def is_banned(user_id: int) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT is_banned FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return bool(row["is_banned"]) if row else False


def ban_user(user_id: int):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def unban_user(user_id: int):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_all_admins():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM users WHERE is_admin = 1 OR is_owner = 1 ORDER BY is_owner DESC"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["permissions"] = json.loads(d.get("permissions") or "{}")
        result.append(d)
    return result


def add_admin(user_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE users SET is_admin = 1, permissions = ? WHERE id = ?",
        (json.dumps(DEFAULT_PERMISSIONS), user_id)
    )
    conn.commit()
    conn.close()


def remove_admin(user_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE users SET is_admin = 0, permissions = '{}' WHERE id = ?", (user_id,)
    )
    conn.commit()
    conn.close()


def update_permissions(user_id: int, perms: dict):
    conn = get_conn()
    conn.execute(
        "UPDATE users SET permissions = ? WHERE id = ?", (json.dumps(perms), user_id)
    )
    conn.commit()
    conn.close()


def get_user_permission(user_id: int, perm: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT is_owner, permissions FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return False
    if row["is_owner"]:
        return True
    perms = json.loads(row["permissions"] or "{}")
    return perms.get(perm, False)


def count_users() -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    conn.close()
    return row["cnt"] if row else 0


def count_active_admins_today() -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE (is_admin=1 OR is_owner=1) AND DATE(last_seen)=DATE('now')"
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ─── Content ─────────────────────────────────────────────────────────────────

def add_content(owner_id, file_id, file_type, raw_text, link_code, delete_after,
                items: list = None) -> int:
    conn = get_conn()
    c = conn.cursor()
    items_json_val = json.dumps(items or [], ensure_ascii=False)
    c.execute("""
        INSERT INTO content (owner_id, file_id, file_type, raw_text, link_code,
                             delete_after, items_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (owner_id, file_id, file_type, raw_text, link_code, delete_after, items_json_val))
    conn.commit()
    row_id = c.lastrowid
    conn.close()
    return row_id


def get_content_by_code(link_code: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM content WHERE link_code = ? AND is_active = 1", (link_code,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_content_by_id(content_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM content WHERE id = ?", (content_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_content(owner_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM content WHERE owner_id = ? AND is_active = 1 ORDER BY created_at DESC",
        (owner_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_content():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM content WHERE is_active = 1 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_content_including_expired():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM content ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expired_content():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM content WHERE is_active = 0 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def deactivate_content(link_code: str):
    conn = get_conn()
    conn.execute("UPDATE content SET is_active = 0 WHERE link_code = ?", (link_code,))
    conn.commit()
    conn.close()


def deactivate_content_by_id(content_id: int):
    conn = get_conn()
    conn.execute("UPDATE content SET is_active = 0 WHERE id = ?", (content_id,))
    conn.commit()
    conn.close()


def delete_all_expired():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM content WHERE is_active = 0").fetchone()
    count = row["cnt"] if row else 0
    conn.execute("DELETE FROM content WHERE is_active = 0")
    conn.commit()
    conn.close()
    return count


def count_all_content() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as cnt FROM content").fetchone()["cnt"]
    active = conn.execute("SELECT COUNT(*) as cnt FROM content WHERE is_active=1").fetchone()["cnt"]
    conn.close()
    return {"total": total, "active": active, "expired": total - active}


def get_popular_content(limit: int = 5):
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.id, c.file_type, c.link_code, COUNT(cv.id) as view_count
        FROM content c
        LEFT JOIN content_views cv ON c.id = cv.content_id
        GROUP BY c.id ORDER BY view_count DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_views(limit: int = 10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT cv.*, c.file_type, c.link_code
        FROM content_views cv
        JOIN content c ON cv.content_id = c.id
        ORDER BY cv.viewed_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_views() -> dict:
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as cnt FROM content_views").fetchone()["cnt"]
    unique = conn.execute("SELECT COUNT(DISTINCT viewer_id) as cnt FROM content_views").fetchone()["cnt"]
    content = conn.execute("SELECT COUNT(*) as cnt FROM content WHERE is_active=1").fetchone()["cnt"]
    conn.close()
    return {"views": total, "unique": unique, "content": content}


# ─── Views ───────────────────────────────────────────────────────────────────

def add_view(content_id: int, viewer_id: int, viewer_name: str, viewer_username: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO content_views (content_id, viewer_id, viewer_name, viewer_username)
        VALUES (?, ?, ?, ?)
    """, (content_id, viewer_id, viewer_name, viewer_username))
    conn.commit()
    conn.close()


def get_content_views(content_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM content_views WHERE content_id = ? ORDER BY viewed_at DESC",
        (content_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_viewers_with_repeats(content_id: int):
    conn = get_conn()
    rows = conn.execute("""
        SELECT viewer_id, viewer_name, viewer_username, COUNT(*) as view_count
        FROM content_views
        WHERE content_id = ?
        GROUP BY viewer_id
        ORDER BY view_count DESC
    """, (content_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_content_views(content_id: int) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM content_views WHERE content_id = ?", (content_id,)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def clear_all_views():
    conn = get_conn()
    conn.execute("DELETE FROM content_views")
    conn.commit()
    conn.close()


# ─── Bot Settings ─────────────────────────────────────────────────────────────

def get_setting(key: str, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO bot_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()


# ─── User States ─────────────────────────────────────────────────────────────

def set_state(user_id: int, state: str, data: dict = None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO user_states (user_id, state, data) VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET state=excluded.state, data=excluded.data
    """, (user_id, state, json.dumps(data or {})))
    conn.commit()
    conn.close()


def get_state(user_id: int):
    conn = get_conn()
    row = conn.execute("SELECT state, data FROM user_states WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row:
        return row["state"], json.loads(row["data"] or "{}")
    return None, {}


def clear_state(user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def clear_all_states():
    conn = get_conn()
    conn.execute("DELETE FROM user_states")
    conn.commit()
    conn.close()


def count_states() -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM user_states").fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ─── Announcements ────────────────────────────────────────────────────────────

def add_announcement(text: str, sent_to: int):
    conn = get_conn()
    conn.execute(
        "INSERT INTO announcements (text, sent_to) VALUES (?, ?)", (text, sent_to)
    )
    conn.commit()
    conn.close()


def get_announcements(limit: int = 10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM announcements ORDER BY sent_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_last_announcement():
    conn = get_conn()
    row = conn.execute("SELECT id FROM announcements ORDER BY sent_at DESC LIMIT 1").fetchone()
    if row:
        conn.execute("DELETE FROM announcements WHERE id = ?", (row["id"],))
        conn.commit()
    conn.close()
    return bool(row)


def clear_announcements():
    conn = get_conn()
    conn.execute("DELETE FROM announcements")
    conn.commit()
    conn.close()


# ─── DB Meta ──────────────────────────────────────────────────────────────────

def get_db_stats() -> dict:
    conn = get_conn()
    users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
    content = conn.execute("SELECT COUNT(*) as cnt FROM content").fetchone()["cnt"]
    views = conn.execute("SELECT COUNT(*) as cnt FROM content_views").fetchone()["cnt"]
    admins = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE is_admin=1 OR is_owner=1").fetchone()["cnt"]
    states = conn.execute("SELECT COUNT(*) as cnt FROM user_states").fetchone()["cnt"]
    conn.close()
    return {"users": users, "content": content, "views": views, "admins": admins, "states": states}


def get_db_size_bytes() -> int:
    import os
    try:
        return os.path.getsize(DB_PATH)
    except Exception:
        return 0


def reset_database():
    conn = get_conn()
    conn.execute("DELETE FROM content_views")
    conn.execute("DELETE FROM content")
    conn.execute("DELETE FROM user_states")
    conn.execute("DELETE FROM announcements")
    conn.execute("DELETE FROM bot_settings")
    conn.execute("UPDATE users SET is_admin=0 WHERE is_owner=0")
    conn.commit()
    conn.close()
