from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.commands import COMMAND_BY_ID
from app.config import settings
from app.db import get_db, get_setting, parse_json_field
from app.services.agents import (
    generate_document_text,
    plain_text_to_html,
    run_analyze_agent,
    run_intent_agent,
    suggested_title,
    update_project_memory,
)
from app.services.ollama import OllamaError
from app.services.orchestrator import run_edit_pipeline
from app.services.text_utils import html_to_plain

router = APIRouter()


class IntentRequest(BaseModel):
    chat_id: int
    document_id: int | None = None
    message: str
    selection_start: int | None = None
    selection_end: int | None = None
    content: str | None = None


class ConfirmRequest(BaseModel):
    chat_id: int
    document_id: int
    message: str
    command_id: str = "custom"
    action_type: str = "edit"
    interpreted_scope: str = "document"
    create_action: str | None = None
    selection_start: int | None = None
    selection_end: int | None = None
    content: str | None = None
    run_fact_check: bool = True


async def _llm_settings(db) -> tuple[str, str, str]:
    url = await get_setting(db, "polza_base_url", settings.polza_ai_base_url)
    model = await get_setting(db, "polza_model", settings.polza_ai_model_name)
    locale = await get_setting(db, "ui_locale", settings.ui_locale)
    return url, model, locale


async def _save_message(db, chat_id: int, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
    await db.execute(
        "INSERT INTO chat_messages (chat_id, role, content, metadata_json) VALUES (?, ?, ?, ?)",
        (chat_id, role, content, json.dumps(metadata or {}, ensure_ascii=False)),
    )
    await db.execute("UPDATE chats SET updated_at = datetime('now') WHERE id = ?", (chat_id,))


@router.post("/api/agent/intent")
async def agent_intent(body: IntentRequest) -> dict[str, Any]:
    db = await get_db()
    try:
        ollama_url, model, locale = await _llm_settings(db)
        excerpt = body.content or ""
        if body.document_id and not excerpt:
            async with db.execute("SELECT content FROM documents WHERE id = ?", (body.document_id,)) as cur:
                row = await cur.fetchone()
                if row:
                    excerpt = html_to_plain(row["content"])
        has_selection = (
            body.selection_start is not None
            and body.selection_end is not None
            and body.selection_start != body.selection_end
        )
        await _save_message(db, body.chat_id, "user", body.message)
        try:
            intent = await run_intent_agent(
                user_message=body.message,
                document_excerpt=excerpt,
                has_selection=has_selection,
                locale=locale,
                ollama_url=ollama_url,
                model=model,
            )
        except OllamaError as e:
            raise HTTPException(502, str(e)) from e
        await _save_message(
            db,
            body.chat_id,
            "assistant",
            intent.get("question") or "",
            {"intent": intent, "awaiting_confirm": bool(intent.get("needs_clarification"))},
        )
        await db.commit()
        return intent
    finally:
        await db.close()


@router.post("/api/agent/confirm")
async def agent_confirm(body: ConfirmRequest) -> dict[str, Any]:
    db = await get_db()
    try:
        ollama_url, model, locale = await _llm_settings(db)
        async with db.execute("SELECT * FROM documents WHERE id = ?", (body.document_id,)) as cur:
            doc = await cur.fetchone()
            if not doc:
                raise HTTPException(404, "Document not found")
        plain = body.content if body.content is not None else html_to_plain(doc["content"])
        project_id = doc["project_id"]

        memory: dict[str, Any] = {}
        if project_id:
            async with db.execute("SELECT memory_json FROM projects WHERE id = ?", (project_id,)) as cur:
                prow = await cur.fetchone()
                memory = parse_json_field(prow["memory_json"] if prow else None)
        async with db.execute(
            "SELECT memory_json FROM document_memory WHERE document_id = ?", (body.document_id,)
        ) as cur:
            mrow = await cur.fetchone()
        doc_memory = parse_json_field(mrow["memory_json"] if mrow else None)
        merged_memory = {**doc_memory, **memory}

        async with db.execute("SELECT profile_json FROM user_style WHERE id = 1") as cur:
            srow = await cur.fetchone()
        style_profile = parse_json_field(srow["profile_json"] if srow else None)

        command_id = body.command_id if body.command_id in COMMAND_BY_ID else "custom"
        preset = COMMAND_BY_ID.get(command_id)
        action = body.action_type
        if preset:
            if preset.action_type == "new_document":
                action = "create"
            elif preset.action_type == "chat_only":
                action = "analyze"

        sel_start = body.selection_start
        sel_end = body.selection_end
        if body.interpreted_scope == "document":
            sel_start = None
            sel_end = None

        result: dict[str, Any] = {"kind": action, "command_id": command_id}

        try:
            if action == "create":
                create_id = body.create_action or command_id
                text = await generate_document_text(
                    command_id=create_id,
                    source_text=plain,
                    custom_instruction=body.message,
                    locale=locale,
                    ollama_url=ollama_url,
                    model=model,
                )
                html = plain_text_to_html(text)
                title = suggested_title(create_id, doc["title"])
                cur = await db.execute(
                    "INSERT INTO documents (title, content, project_id, chat_id, source, file_name) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (title, html, project_id, body.chat_id, "ai", title),
                )
                new_id = cur.lastrowid
                await db.execute(
                    "INSERT INTO versions (document_id, label, content, command_id) VALUES (?, ?, ?, ?)",
                    (new_id, "AI", html, create_id),
                )
                await db.execute(
                    "INSERT INTO document_memory (document_id, memory_json) VALUES (?, '{}')",
                    (new_id,),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO chat_documents (chat_id, document_id) VALUES (?, ?)",
                    (body.chat_id, new_id),
                )
                result.update({"kind": "create", "document_id": new_id, "title": title, "content": html})
                await _save_message(
                    db,
                    body.chat_id,
                    "assistant",
                    f"Created document: {title}",
                    {"created_document_id": new_id},
                )
            elif action == "analyze":
                analysis = await run_analyze_agent(
                    command_id=command_id,
                    document_text=plain,
                    custom_instruction=body.message,
                    locale=locale,
                    ollama_url=ollama_url,
                    model=model,
                )
                await _save_message(db, body.chat_id, "assistant", analysis, {"kind": "analyze"})
                result.update({"kind": "analyze", "text": analysis})
            else:
                pipeline = await run_edit_pipeline(
                    full_text=plain,
                    selection_start=sel_start,
                    selection_end=sel_end,
                    command_id=command_id,
                    custom_instruction=body.message,
                    memory=merged_memory,
                    style_profile=style_profile,
                    locale=locale,
                    ollama_url=ollama_url,
                    model=model,
                    run_fact_check=body.run_fact_check,
                )
                pipeline["proposed_html"] = plain_text_to_html(pipeline["proposed_full_text"])
                await _save_message(
                    db,
                    body.chat_id,
                    "assistant",
                    "Ready. Review the preview and accept or reject.",
                    {"kind": "edit_preview", "command_id": command_id},
                )
                result.update({"kind": "edit", "proposal": pipeline})
        except OllamaError as e:
            raise HTTPException(502, str(e)) from e

        await db.commit()
        return result
    finally:
        await db.close()


@router.post("/api/documents/generate")
async def generate_document(body: ConfirmRequest) -> dict[str, Any]:
    body.action_type = "create"
    return await agent_confirm(body)
