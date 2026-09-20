from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_db, parse_json_field

router = APIRouter()


class ProjectCreate(BaseModel):
    title: str = "Workspace"


class ChatCreate(BaseModel):
    project_id: int | None = None
    title: str = "New chat"


class ChatPatch(BaseModel):
    title: str | None = None
    pinned: bool | None = None


class MessageCreate(BaseModel):
    role: str = "user"
    content: str
    metadata: dict[str, Any] | None = None


class DocumentCreate(BaseModel):
    title: str = "Untitled"
    content: str = ""
    project_id: int | None = None
    chat_id: int | None = None
    source: str = "user"
    file_name: str | None = None


async def _default_project_id(db) -> int:
    async with db.execute("SELECT id FROM projects ORDER BY id ASC LIMIT 1") as cur:
        row = await cur.fetchone()
        if not row:
            raise HTTPException(500, "No workspace project")
        return int(row["id"])


@router.get("/api/projects")
async def list_projects() -> list[dict[str, Any]]:
    db = await get_db()
    try:
        async with db.execute(
            "SELECT id, title, memory_json, updated_at FROM projects ORDER BY updated_at DESC"
        ) as cur:
            rows = await cur.fetchall()
            return [
                {
                    **{k: r[k] for k in r.keys() if k != "memory_json"},
                    "memory": parse_json_field(r["memory_json"]),
                }
                for r in rows
            ]
    finally:
        await db.close()


@router.post("/api/projects")
async def create_project(body: ProjectCreate) -> dict[str, Any]:
    db = await get_db()
    try:
        cur = await db.execute("INSERT INTO projects (title) VALUES (?)", (body.title,))
        await db.commit()
        return {"id": cur.lastrowid, "title": body.title}
    finally:
        await db.close()


@router.get("/api/chats")
async def list_chats(project_id: int | None = None) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        if project_id:
            q = (
                "SELECT * FROM chats WHERE project_id = ? "
                "ORDER BY COALESCE(pinned, 0) DESC, updated_at DESC"
            )
            args: tuple[Any, ...] = (project_id,)
        else:
            q = "SELECT * FROM chats ORDER BY COALESCE(pinned, 0) DESC, updated_at DESC"
            args = ()
        async with db.execute(q, args) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
            for r in rows:
                r["pinned"] = bool(r.get("pinned"))
            return rows
    finally:
        await db.close()


@router.post("/api/chats")
async def create_chat(body: ChatCreate) -> dict[str, Any]:
    db = await get_db()
    try:
        project_id = body.project_id or await _default_project_id(db)
        cur = await db.execute(
            "INSERT INTO chats (project_id, title) VALUES (?, ?)",
            (project_id, body.title),
        )
        chat_id = cur.lastrowid
        cur = await db.execute(
            "INSERT INTO documents (title, content, project_id, chat_id, source) VALUES (?, ?, ?, ?, ?)",
            ("Untitled", "<p></p>", project_id, chat_id, "user"),
        )
        doc_id = cur.lastrowid
        await db.execute(
            "INSERT INTO versions (document_id, label, content, command_id) VALUES (?, ?, ?, ?)",
            (doc_id, "Original", "<p></p>", "original"),
        )
        await db.execute(
            "INSERT INTO document_memory (document_id, memory_json) VALUES (?, '{}')",
            (doc_id,),
        )
        await db.execute(
            "INSERT OR IGNORE INTO chat_documents (chat_id, document_id) VALUES (?, ?)",
            (chat_id, doc_id),
        )
        await db.commit()
        return {"id": chat_id, "project_id": project_id, "title": body.title, "document_id": doc_id}
    finally:
        await db.close()


@router.get("/api/chats/{chat_id}")
async def get_chat(chat_id: int) -> dict[str, Any]:
    db = await get_db()
    try:
        async with db.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Chat not found")
        async with db.execute(
            "SELECT document_id FROM chat_documents WHERE chat_id = ?", (chat_id,)
        ) as cur:
            docs = [r["document_id"] for r in await cur.fetchall()]
        data = {**dict(row), "document_ids": docs}
        data["pinned"] = bool(data.get("pinned"))
        return data
    finally:
        await db.close()


@router.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: int) -> dict[str, bool]:
    db = await get_db()
    try:
        async with db.execute("SELECT id FROM chats WHERE id = ?", (chat_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, "Chat not found")
        await db.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@router.patch("/api/chats/{chat_id}")
async def patch_chat(chat_id: int, body: ChatPatch) -> dict[str, Any]:
    db = await get_db()
    try:
        updates: list[str] = []
        args: list[Any] = []
        if body.title is not None:
            title = body.title.strip() or "New chat"
            updates.append("title = ?")
            args.append(title)
        if body.pinned is not None:
            updates.append("pinned = ?")
            args.append(1 if body.pinned else 0)
        if updates:
            updates.append("updated_at = datetime('now')")
            args.append(chat_id)
            await db.execute(
                f"UPDATE chats SET {', '.join(updates)} WHERE id = ?",
                args,
            )
            await db.commit()
        return await get_chat(chat_id)
    finally:
        await db.close()


@router.get("/api/chats/{chat_id}/messages")
async def list_messages(chat_id: int) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM chat_messages WHERE chat_id = ? ORDER BY id ASC",
            (chat_id,),
        ) as cur:
            rows = await cur.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                item["metadata"] = parse_json_field(item.pop("metadata_json", None))
                result.append(item)
            return result
    finally:
        await db.close()


@router.post("/api/chats/{chat_id}/messages")
async def add_message(chat_id: int, body: MessageCreate) -> dict[str, Any]:
    db = await get_db()
    try:
        import json

        cur = await db.execute(
            "INSERT INTO chat_messages (chat_id, role, content, metadata_json) VALUES (?, ?, ?, ?)",
            (chat_id, body.role, body.content, json.dumps(body.metadata or {}, ensure_ascii=False)),
        )
        await db.execute(
            "UPDATE chats SET updated_at = datetime('now') WHERE id = ?", (chat_id,)
        )
        await db.commit()
        return {"id": cur.lastrowid, "role": body.role, "content": body.content}
    finally:
        await db.close()


@router.post("/api/workspace/bootstrap")
async def bootstrap_workspace() -> dict[str, Any]:
    db = await get_db()
    try:
        project_id = await _default_project_id(db)
        async with db.execute(
            "SELECT * FROM chats WHERE project_id = ? ORDER BY updated_at DESC LIMIT 1",
            (project_id,),
        ) as cur:
            chat = await cur.fetchone()
        if chat:
            doc_id: int | None = None
            async with db.execute(
                "SELECT document_id FROM chat_documents WHERE chat_id = ? LIMIT 1",
                (chat["id"],),
            ) as cur:
                row = await cur.fetchone()
                if row:
                    doc_id = int(row["document_id"])
            if doc_id is None:
                async with db.execute(
                    "SELECT id FROM documents WHERE chat_id = ? ORDER BY id DESC LIMIT 1",
                    (chat["id"],),
                ) as cur:
                    row = await cur.fetchone()
                    if row:
                        doc_id = int(row["id"])
            if doc_id is not None:
                return {
                    "id": chat["id"],
                    "project_id": project_id,
                    "title": chat["title"],
                    "document_id": doc_id,
                }
            cur = await db.execute(
                "INSERT INTO documents (title, content, project_id, chat_id, source) VALUES (?, ?, ?, ?, ?)",
                ("Untitled", "<p></p>", project_id, chat["id"], "user"),
            )
            doc_id = int(cur.lastrowid)
            await db.execute(
                "INSERT INTO versions (document_id, label, content, command_id) VALUES (?, ?, ?, ?)",
                (doc_id, "Original", "<p></p>", "original"),
            )
            await db.execute(
                "INSERT INTO document_memory (document_id, memory_json) VALUES (?, '{}')",
                (doc_id,),
            )
            await db.execute(
                "INSERT OR IGNORE INTO chat_documents (chat_id, document_id) VALUES (?, ?)",
                (chat["id"], doc_id),
            )
            await db.commit()
            return {
                "id": chat["id"],
                "project_id": project_id,
                "title": chat["title"],
                "document_id": doc_id,
            }
    finally:
        await db.close()
    return await create_chat(ChatCreate(project_id=None))
