import json
import sqlite3
import time
import uuid
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY,
  title TEXT,
  project TEXT,
  created_at REAL,
  updated_at REAL
);
CREATE TABLE IF NOT EXISTS messages(
  id TEXT PRIMARY KEY,
  session_id TEXT,
  role TEXT,
  content TEXT,
  attachments TEXT,
  created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
CREATE TABLE IF NOT EXISTS project_memory(
  project TEXT,
  key TEXT,
  value TEXT,
  updated_at REAL,
  PRIMARY KEY(project, key)
);
"""


def _conn():
    cfg = config.load()
    db = Path(cfg.get("db_path") or Path(config.APP_HOME) / "memory.db")
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def new_session(title="新任务", project=""):
    sid = uuid.uuid4().hex[:12]
    now = time.time()
    conn = _conn()
    try:
        with conn:
            conn.execute(
                "INSERT INTO sessions(id,title,project,created_at,updated_at) VALUES(?,?,?,?,?)",
                (sid, title, project, now, now),
            )
    finally:
        conn.close()
    return sid


def list_sessions():
    conn = _conn()
    try:
        rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_session(sid):
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_project(sid, project):
    conn = _conn()
    try:
        with conn:
            conn.execute(
                "UPDATE sessions SET project=?, updated_at=? WHERE id=?",
                (project, time.time(), sid),
            )
    finally:
        conn.close()


def touch(sid):
    conn = _conn()
    try:
        with conn:
            conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (time.time(), sid))
    finally:
        conn.close()


def add_message(sid, role, content, attachments=None):
    mid = uuid.uuid4().hex
    conn = _conn()
    try:
        with conn:
            conn.execute(
                "INSERT INTO messages(id,session_id,role,content,attachments,created_at) VALUES(?,?,?,?,?,?)",
                (mid, sid, role, content, json.dumps(attachments or [], ensure_ascii=False), time.time()),
            )
    finally:
        conn.close()
    touch(sid)
    return mid


def messages(sid, limit=None):
    conn = _conn()
    try:
        q = "SELECT * FROM messages WHERE session_id=? ORDER BY created_at ASC, rowid ASC"
        rows = conn.execute(q, (sid,)).fetchall()
        out = [dict(r) for r in rows]
        for m in out:
            try:
                m["attachments"] = json.loads(m.get("attachments") or "[]")
            except Exception:
                m["attachments"] = []
        if limit:
            out = out[-limit:]
        return out
    finally:
        conn.close()


def delete_session(sid):
    conn = _conn()
    try:
        with conn:
            conn.execute("DELETE FROM messages WHERE session_id=?", (sid,))
            conn.execute("DELETE FROM sessions WHERE id=?", (sid,))
    finally:
        conn.close()


def mem_set(project, key, value):
    conn = _conn()
    try:
        with conn:
            conn.execute(
                "INSERT INTO project_memory(project,key,value,updated_at) VALUES(?,?,?,?) "
                "ON CONFLICT(project,key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (project, key, value, time.time()),
            )
    finally:
        conn.close()


def mem_get(project, key):
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT value FROM project_memory WHERE project=? AND key=?", (project, key)
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def mem_all(project):
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT key,value FROM project_memory WHERE project=? ORDER BY key", (project,)
        ).fetchall()
        return {r["key"]: r["value"] for r in rows}
    finally:
        conn.close()


def mem_delete(project, key):
    conn = _conn()
    try:
        with conn:
            conn.execute("DELETE FROM project_memory WHERE project=? AND key=?", (project, key))
    finally:
        conn.close()
