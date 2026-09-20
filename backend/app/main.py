from __future__ import annotations

import json
import logging
import re
from typing import Any

import aiosqlite
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.commands import COMMAND_PRESETS
from app.config import settings
from app.db import get_db, get_setting, parse_json_field, set_setting
from app.routes.agent import router as agent_router
from app.routes.workspace import router as workspace_router
from app.services.agents import (
    plain_text_to_html,
    refine_style_profile,
    update_document_memory,
    update_project_memory,
)
from app.services.export_formats import export_docx, export_html, export_md, export_pdf, export_txt
from app.services.import_parsers import extract_text_from_bytes
from app.services.ollama import OllamaError
from app.services.orchestrator import run_edit_pipeline
from app.services.text_utils import html_to_plain

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Text Editor API", version="0.1.0")


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception("Unhandled API error")
    detail = str(exc).strip() or exc.__class__.__name__
    if isinstance(exc, aiosqlite.Error):
        detail = f"Database error: {detail}"
    return JSONResponse(status_code=500, content={"detail": detail})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(workspace_router)
app.include_router(agent_router)


class DocumentCreate(BaseModel):
    title: str = "Untitled"
    content: str = ""
    project_id: int | None = None
    chat_id: int | None = None
    source: str = "user"
    file_name: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class EditRequest(BaseModel):
    command_id: str = "improve"
    custom_instruction: str | None = None
    selection_start: int | None = None
    selection_end: int | None = None
    content: str | None = None
    run_fact_check: bool = True


class AcceptProposal(BaseModel):
    proposed_full_text: str
    command_id: str
    custom_instruction: str | None = None
    label: str | None = None


class SettingsUpdate(BaseModel):
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    polza_base_url: str | None = None
    polza_model: str | None = None
    ui_locale: str | None = None


@app.on_event("startup")
async def startup() -> None:
    db = await get_db()
    await db.close()


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse("http://127.0.0.1:5173/")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/commands")
async def list_commands() -> list[dict[str, Any]]:
    return [
        {
            "id": c.id,
            "i18nKey": c.i18n_key,
            "category": c.category,
            "actionType": c.action_type,
        }
        for c in COMMAND_PRESETS
    ]


@app.get("/api/settings")
async def read_settings() -> dict[str, Any]:
    db = await get_db()
    try:
        polza_url = await get_setting(db, "polza_base_url", settings.polza_ai_base_url)
        polza_model = await get_setting(db, "polza_model", settings.polza_ai_model_name)
        ui_locale = await get_setting(db, "ui_locale", settings.ui_locale)
        has_key = bool(settings.polza_ai_api_key.strip())
        return {
            "ollama_base_url": polza_url,
            "ollama_model": polza_model,
            "polza_base_url": polza_url,
            "polza_model": polza_model,
            "ui_locale": ui_locale,
            "ollama_connected": has_key,
            "polza_connected": has_key,
            "ollama_error": None if has_key else "POLZA_AI_API_KEY is missing",
        }
    finally:
        await db.close()


@app.patch("/api/settings")
async def patch_settings(body: SettingsUpdate) -> dict[str, Any]:
    db = await get_db()
    try:
        url = body.polza_base_url or body.ollama_base_url
        model = body.polza_model or body.ollama_model
        if url is not None:
            await set_setting(db, "polza_base_url", url)
        if model is not None:
            await set_setting(db, "polza_model", model)
        if body.ui_locale is not None:
            await set_setting(db, "ui_locale", body.ui_locale)
        return await read_settings()
    finally:
        await db.close()


@app.get("/api/documents")
async def list_documents(project_id: int | None = None) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        if project_id:
            q = (
                "SELECT id, title, updated_at, project_id, chat_id, source, file_name "
                "FROM documents WHERE project_id = ? ORDER BY updated_at DESC"
            )
            args: tuple[Any, ...] = (project_id,)
        else:
            q = (
                "SELECT id, title, updated_at, project_id, chat_id, source, file_name "
                "FROM documents ORDER BY updated_at DESC"
            )
            args = ()
        async with db.execute(q, args) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        await db.close()


@app.post("/api/documents")
async def create_document(body: DocumentCreate) -> dict[str, Any]:
    db = await get_db()
    try:
        cur = await db.execute(
            "INSERT INTO documents (title, content, project_id, chat_id, source, file_name) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (body.title, body.content, body.project_id, body.chat_id, body.source, body.file_name),
        )
        doc_id = cur.lastrowid
        await db.execute(
            "INSERT INTO versions (document_id, label, content, command_id) VALUES (?, ?, ?, ?)",
            (doc_id, "Original", body.content, "original"),
        )
        await db.execute(
            "INSERT INTO document_memory (document_id, memory_json) VALUES (?, ?)",
            (doc_id, "{}"),
        )
        await db.commit()
        return {"id": doc_id, "title": body.title, "content": body.content}
    finally:
        await db.close()


async def _document_payload(db: aiosqlite.Connection, doc_id: int) -> dict[str, Any]:
    async with db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)) as cur:
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Document not found")
    async with db.execute(
        "SELECT memory_json FROM document_memory WHERE document_id = ?", (doc_id,)
    ) as cur:
        mem = await cur.fetchone()
    async with db.execute("SELECT profile_json FROM user_style WHERE id = 1") as cur:
        style = await cur.fetchone()
    return {
        **dict(row),
        "memory": parse_json_field(mem["memory_json"] if mem else None),
        "style_profile": parse_json_field(style["profile_json"] if style else None),
    }


@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: int) -> dict[str, Any]:
    db = await get_db()
    try:
        return await _document_payload(db, doc_id)
    finally:
        await db.close()


@app.patch("/api/documents/{doc_id}")
async def update_document(doc_id: int, body: DocumentUpdate) -> dict[str, Any]:
    db = await get_db()
    try:
        async with db.execute("SELECT id FROM documents WHERE id = ?", (doc_id,)) as cur:
            if not await cur.fetchone():
                raise HTTPException(404, "Document not found")
        if body.title is not None:
            await db.execute(
                "UPDATE documents SET title = ?, updated_at = datetime('now') WHERE id = ?",
                (body.title, doc_id),
            )
        if body.content is not None:
            await db.execute(
                "UPDATE documents SET content = ?, updated_at = datetime('now') WHERE id = ?",
                (body.content, doc_id),
            )
        await db.commit()
        return await _document_payload(db, doc_id)
    finally:
        await db.close()


_EXPORT_HANDLERS: dict[str, tuple[str, str, Any]] = {
    "txt": ("text/plain; charset=utf-8", ".txt", export_txt),
    "md": ("text/markdown; charset=utf-8", ".md", export_md),
    "html": ("text/html; charset=utf-8", ".html", export_html),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
        export_docx,
    ),
    "pdf": ("application/pdf", ".pdf", export_pdf),
}


def _safe_filename(title: str, ext: str) -> str:
    base = re.sub(r"[^\w\s\-.]", "", title, flags=re.UNICODE).strip() or "document"
    base = re.sub(r"\s+", "_", base)[:80]
    return f"{base}{ext}"


@app.get("/api/documents/{doc_id}/export")
async def export_document(doc_id: int, format: str = "txt") -> Response:
    fmt = format.lower().strip()
    if fmt not in _EXPORT_HANDLERS:
        raise HTTPException(400, f"Unsupported format: {format}")
    media_type, ext, handler = _EXPORT_HANDLERS[fmt]
    db = await get_db()
    try:
        async with db.execute(
            "SELECT title, content FROM documents WHERE id = ?", (doc_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Document not found")
        title = row["title"] or "document"
        html = row["content"] or ""
        try:
            if fmt in ("md", "html", "docx", "pdf"):
                data = handler(html, title)
            else:
                data = handler(html)
        except Exception as e:
            raise HTTPException(400, f"Export failed: {e}") from e
        filename = _safe_filename(title, ext)
        return Response(
            content=data,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        await db.close()


@app.get("/api/documents/{doc_id}/versions")
async def list_versions(doc_id: int) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        async with db.execute(
            "SELECT id, label, command_id, custom_instruction, created_at, parent_version_id "
            "FROM versions WHERE document_id = ? ORDER BY id ASC",
            (doc_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        await db.close()


@app.get("/api/documents/{doc_id}/versions/{version_id}")
async def get_version(doc_id: int, version_id: int) -> dict[str, Any]:
    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM versions WHERE id = ? AND document_id = ?",
            (version_id, doc_id),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Version not found")
            return dict(row)
    finally:
        await db.close()


@app.post("/api/documents/{doc_id}/restore/{version_id}")
async def restore_version(doc_id: int, version_id: int) -> dict[str, Any]:
    db = await get_db()
    try:
        async with db.execute(
            "SELECT content FROM versions WHERE id = ? AND document_id = ?",
            (version_id, doc_id),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Version not found")
        content = row["content"]
        await db.execute(
            "UPDATE documents SET content = ?, updated_at = datetime('now') WHERE id = ?",
            (content, doc_id),
        )
        await db.commit()
        return {"content": content}
    finally:
        await db.close()


@app.post("/api/documents/{doc_id}/import")
async def import_file(doc_id: int, file: UploadFile = File(...)) -> dict[str, Any]:
    data = await file.read()
    try:
        text = extract_text_from_bytes(file.filename or "doc.txt", data)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    html = plain_text_to_html(text)
    db = await get_db()
    try:
        await db.execute(
            "UPDATE documents SET content = ?, title = COALESCE(NULLIF(title, 'Untitled'), ?), updated_at = datetime('now') WHERE id = ?",
            (html, file.filename or "Import", doc_id),
        )
        await db.execute(
            "INSERT INTO versions (document_id, label, content, command_id) VALUES (?, ?, ?, ?)",
            (doc_id, "Import", html, "import"),
        )
        await db.commit()
    finally:
        await db.close()
    return {"content": html, "plain_length": len(text)}


@app.post("/api/documents/{doc_id}/edit")
async def propose_edit(doc_id: int, body: EditRequest) -> dict[str, Any]:
    db = await get_db()
    try:
        async with db.execute("SELECT content FROM documents WHERE id = ?", (doc_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Document not found")
        content_html = row["content"]
        if body.content is not None:
            plain = body.content
        else:
            plain = html_to_plain(content_html)

        ollama_url = await get_setting(db, "polza_base_url", settings.polza_ai_base_url)
        ollama_model = await get_setting(db, "polza_model", settings.polza_ai_model_name)
        ui_locale = await get_setting(db, "ui_locale", settings.ui_locale)

        async with db.execute(
            "SELECT memory_json FROM document_memory WHERE document_id = ?", (doc_id,)
        ) as cur:
            mem_row = await cur.fetchone()
        memory = parse_json_field(mem_row["memory_json"] if mem_row else None)

        async with db.execute("SELECT profile_json FROM user_style WHERE id = 1") as cur:
            style_row = await cur.fetchone()
        style_profile = parse_json_field(style_row["profile_json"] if style_row else None)

        try:
            result = await run_edit_pipeline(
                full_text=plain,
                selection_start=body.selection_start,
                selection_end=body.selection_end,
                command_id=body.command_id,
                custom_instruction=body.custom_instruction,
                memory=memory,
                style_profile=style_profile,
                locale=ui_locale,
                ollama_url=ollama_url,
                model=ollama_model,
                run_fact_check=body.run_fact_check,
            )
        except OllamaError as e:
            raise HTTPException(502, str(e)) from e

        result["proposed_html"] = plain_text_to_html(result["proposed_full_text"])
        result["original_html"] = content_html
        return result
    finally:
        await db.close()


@app.post("/api/documents/{doc_id}/accept")
async def accept_edit(doc_id: int, body: AcceptProposal) -> dict[str, Any]:
    db = await get_db()
    try:
        async with db.execute("SELECT content, project_id FROM documents WHERE id = ?", (doc_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Document not found")
        before_plain = html_to_plain(row["content"])
        after_html = plain_text_to_html(body.proposed_full_text)
        label = body.label or body.command_id

        async with db.execute(
            "SELECT id FROM versions WHERE document_id = ? ORDER BY id DESC LIMIT 1",
            (doc_id,),
        ) as cur:
            last = await cur.fetchone()
        parent_id = last["id"] if last else None

        await db.execute(
            "UPDATE documents SET content = ?, updated_at = datetime('now') WHERE id = ?",
            (after_html, doc_id),
        )
        cur = await db.execute(
            "INSERT INTO versions (document_id, label, content, command_id, custom_instruction, parent_version_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, label, after_html, body.command_id, body.custom_instruction, parent_id),
        )
        version_id = cur.lastrowid

        ollama_url = await get_setting(db, "polza_base_url", settings.polza_ai_base_url)
        ollama_model = await get_setting(db, "polza_model", settings.polza_ai_model_name)

        new_memory: dict[str, Any] = {}
        try:
            async with db.execute(
                "SELECT memory_json FROM document_memory WHERE document_id = ?", (doc_id,)
            ) as cur:
                mem_row = await cur.fetchone()
            memory = parse_json_field(mem_row["memory_json"] if mem_row else None)

            instruction = body.custom_instruction or body.command_id
            new_memory = await update_document_memory(
                current_memory=memory,
                document_excerpt=body.proposed_full_text,
                last_instruction=instruction,
                ollama_url=ollama_url,
                model=ollama_model,
            )
            await db.execute(
                "UPDATE document_memory SET memory_json = ?, updated_at = datetime('now') WHERE document_id = ?",
                (json.dumps(new_memory, ensure_ascii=False), doc_id),
            )

            project_id = row["project_id"]
            if project_id:
                async with db.execute(
                    "SELECT memory_json FROM projects WHERE id = ?", (project_id,)
                ) as cur:
                    prow = await cur.fetchone()
                pm = parse_json_field(prow["memory_json"] if prow else None)
                async with db.execute(
                    "SELECT title FROM documents WHERE project_id = ?", (project_id,)
                ) as cur:
                    titles = [r["title"] for r in await cur.fetchall()]
                pm = await update_project_memory(
                    current_memory=pm,
                    document_excerpt=body.proposed_full_text,
                    last_instruction=instruction,
                    linked_files=titles,
                    ollama_url=ollama_url,
                    model=ollama_model,
                )
                await db.execute(
                    "UPDATE projects SET memory_json = ?, updated_at = datetime('now') WHERE id = ?",
                    (json.dumps(pm, ensure_ascii=False), project_id),
                )
                new_memory = {**new_memory, "project": pm}

            async with db.execute("SELECT profile_json FROM user_style WHERE id = 1") as cur:
                style_row = await cur.fetchone()
            profile = parse_json_field(style_row["profile_json"] if style_row else None)
            new_profile = await refine_style_profile(
                profile,
                before_plain,
                body.proposed_full_text,
                ollama_url,
                ollama_model,
            )
            await db.execute(
                "UPDATE user_style SET profile_json = ?, updated_at = datetime('now') WHERE id = 1",
                (json.dumps(new_profile, ensure_ascii=False),),
            )
        except OllamaError:
            pass

        await db.commit()
        return {"version_id": version_id, "content": after_html, "memory": new_memory}
    finally:
        await db.close()
