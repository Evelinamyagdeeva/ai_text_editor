from __future__ import annotations

import json
from typing import Any

import aiosqlite

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT 'Workspace',
    memory_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT 'New chat',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT 'Untitled',
    content TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_documents (
    chat_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    PRIMARY KEY (chat_id, document_id),
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    content TEXT NOT NULL,
    command_id TEXT,
    custom_instruction TEXT,
    parent_version_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS document_memory (
    document_id INTEGER PRIMARY KEY,
    memory_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_style (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    profile_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_versions_doc ON versions(document_id);
CREATE INDEX IF NOT EXISTS idx_chats_project ON chats(project_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON chat_messages(chat_id);
"""

DOC_COLUMNS = {
    "project_id": "INTEGER",
    "chat_id": "INTEGER",
    "source": "TEXT NOT NULL DEFAULT 'user'",
    "file_name": "TEXT",
}

CHAT_COLUMNS = {
    "pinned": "INTEGER NOT NULL DEFAULT 0",
}


async def _ensure_columns(db: aiosqlite.Connection) -> None:
    async with db.execute("PRAGMA table_info(documents)") as cur:
        existing = {row["name"] for row in await cur.fetchall()}
    for name, decl in DOC_COLUMNS.items():
        if name not in existing:
            await db.execute(f"ALTER TABLE documents ADD COLUMN {name} {decl}")
    async with db.execute("PRAGMA table_info(chats)") as cur:
        chat_existing = {row["name"] for row in await cur.fetchall()}
    for name, decl in CHAT_COLUMNS.items():
        if name not in chat_existing:
            await db.execute(f"ALTER TABLE chats ADD COLUMN {name} {decl}")


async def _ensure_default_workspace(db: aiosqlite.Connection) -> None:
    async with db.execute("SELECT id FROM projects LIMIT 1") as cur:
        row = await cur.fetchone()
    if row:
        return
    cur = await db.execute("INSERT INTO projects (title) VALUES (?)", ("Main",))
    project_id = cur.lastrowid
    await db.execute(
        "INSERT INTO chats (project_id, title) VALUES (?, ?)",
        (project_id, "New chat"),
    )
    await db.execute(
        "UPDATE documents SET project_id = COALESCE(project_id, ?) WHERE project_id IS NULL",
        (project_id,),
    )


async def get_db() -> aiosqlite.Connection:
    path = settings.resolved_db_path()
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.executescript(SCHEMA)
    await _ensure_columns(db)
    await db.execute(
        "INSERT OR IGNORE INTO user_style (id, profile_json) VALUES (1, '{}')"
    )
    await _ensure_default_workspace(db)
    await db.commit()
    return db


async def get_setting(db: aiosqlite.Connection, key: str, default: str = "") -> str:
    async with db.execute("SELECT value FROM app_settings WHERE key = ?", (key,)) as cur:
        row = await cur.fetchone()
        return row["value"] if row else default


async def set_setting(db: aiosqlite.Connection, key: str, value: str) -> None:
    await db.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    await db.commit()


def parse_json_field(raw: str | None, default: Any = None) -> Any:
    if default is None:
        default = {}
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default
