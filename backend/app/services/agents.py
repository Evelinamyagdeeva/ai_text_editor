from __future__ import annotations

import json
import re
from typing import Any

from app.commands import PRESET_INSTRUCTIONS
from app.services.ollama import chat, parse_json_response


def _build_edit_messages(
    *,
    full_document: str,
    target_text: str,
    instruction: str,
    memory: dict[str, Any],
    style_profile: dict[str, Any],
    locale: str,
) -> list[dict[str, str]]:
    memory_block = json.dumps(memory, ensure_ascii=False) if memory else "{}"
    style_block = json.dumps(style_profile, ensure_ascii=False) if style_profile else "{}"
    system = (
        "You are an intelligent text editor assistant. "
        "Edit ONLY the TARGET passage. Return the revised TARGET text only—no quotes, no explanation. "
        "Use the FULL DOCUMENT for context (tone, terms, continuity) but do not rewrite parts outside TARGET. "
        "Never invent facts. Preserve the user's intent.\n"
        f"User UI locale: {locale}. Keep the edited passage in the same language as the TARGET unless translation was requested.\n"
        f"Document memory: {memory_block}\n"
        f"User style preferences (when relevant): {style_block}\n"
    )
    user = (
        f"INSTRUCTION:\n{instruction}\n\n"
        f"FULL DOCUMENT:\n{full_document}\n\n"
        f"TARGET (edit this only):\n{target_text}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def run_edit_agent(
    *,
    full_document: str,
    target_text: str,
    command_id: str,
    custom_instruction: str | None,
    memory: dict[str, Any],
    style_profile: dict[str, Any],
    locale: str,
    ollama_url: str,
    model: str,
    retry_hint: str | None = None,
) -> str:
    base_instruction = PRESET_INSTRUCTIONS.get(command_id, PRESET_INSTRUCTIONS["custom"])
    if custom_instruction:
        base_instruction = f"{base_instruction}\n\nAdditional user instructions:\n{custom_instruction}"
    if retry_hint:
        base_instruction = f"{base_instruction}\n\nCritic feedback to address:\n{retry_hint}"

    messages = _build_edit_messages(
        full_document=full_document,
        target_text=target_text,
        instruction=base_instruction,
        memory=memory,
        style_profile=style_profile,
        locale=locale,
    )
    return await chat(messages, base_url=ollama_url, model=model, temperature=0.35)


async def run_critic_agent(
    *,
    original_target: str,
    edited_target: str,
    instruction: str,
    ollama_url: str,
    model: str,
) -> dict[str, Any]:
    system = (
        "You are a strict editing critic. Respond with JSON only:\n"
        '{"pass": boolean, "issues": string[], "retry_prompt": string}\n'
        "Check: meaning preserved, no lost important info, no new facts, matches instruction, "
        "not overly formal unless asked, no redundant repetition."
    )
    user = (
        f"INSTRUCTION:\n{instruction}\n\n"
        f"ORIGINAL:\n{original_target}\n\n"
        f"EDITED:\n{edited_target}"
    )
    raw = await chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        base_url=ollama_url,
        model=model,
        format_json=True,
        temperature=0.1,
    )
    try:
        data = parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        return {"pass": True, "issues": [], "retry_prompt": ""}
    data.setdefault("pass", True)
    data.setdefault("issues", [])
    data.setdefault("retry_prompt", "")
    return data


async def extract_fact_claims(text: str, ollama_url: str, model: str) -> list[dict[str, str]]:
    system = (
        "Extract factual claims that a reader might want to verify. "
        'Return JSON: {"claims": [{"quote": "...", "reason": "..."}]}. '
        "Max 5 claims. Do not judge truth."
    )
    raw = await chat(
        [{"role": "system", "content": system}, {"role": "user", "content": text[:8000]}],
        base_url=ollama_url,
        model=model,
        format_json=True,
        temperature=0.1,
    )
    try:
        data = parse_json_response(raw)
        return list(data.get("claims") or [])
    except (json.JSONDecodeError, ValueError):
        return []


async def update_document_memory(
    *,
    current_memory: dict[str, Any],
    document_excerpt: str,
    last_instruction: str,
    ollama_url: str,
    model: str,
) -> dict[str, Any]:
    system = (
        "Update document memory for a long-running writing project. "
        'Return JSON with keys: topic, goal, audience, style, key_terms (string[]), notes. '
        "Merge with existing memory; keep concise."
    )
    user = json.dumps(
        {
            "existing_memory": current_memory,
            "document_excerpt": document_excerpt[:6000],
            "last_instruction": last_instruction,
        },
        ensure_ascii=False,
    )
    raw = await chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        base_url=ollama_url,
        model=model,
        format_json=True,
        temperature=0.2,
    )
    try:
        updated = parse_json_response(raw)
        merged = {**current_memory, **updated}
        return merged
    except (json.JSONDecodeError, ValueError):
        return current_memory


async def update_project_memory(
    *,
    current_memory: dict[str, Any],
    document_excerpt: str,
    last_instruction: str,
    linked_files: list[str],
    ollama_url: str,
    model: str,
) -> dict[str, Any]:
    system = (
        "Update project memory for a writing workspace. "
        "Return JSON with keys: topic, goal, audience, style, key_terms (string[]), "
        "linked_files (string[]), recent_actions (string[]), notes. Merge; keep concise."
    )
    user = json.dumps(
        {
            "existing_memory": current_memory,
            "document_excerpt": document_excerpt[:6000],
            "last_instruction": last_instruction,
            "linked_files": linked_files,
        },
        ensure_ascii=False,
    )
    raw = await chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        base_url=ollama_url,
        model=model,
        format_json=True,
        temperature=0.2,
    )
    try:
        updated = parse_json_response(raw)
        merged = {**current_memory, **updated}
        return merged
    except (json.JSONDecodeError, ValueError):
        return current_memory


async def run_intent_agent(
    *,
    user_message: str,
    document_excerpt: str,
    has_selection: bool,
    locale: str,
    ollama_url: str,
    model: str,
) -> dict[str, Any]:
    system = (
        "You classify a user's request for a document editor. Reply JSON only:\n"
        "{"
        '"needs_clarification": boolean, '
        '"question": string, '
        '"interpreted_scope": "selection"|"document"|"create_file", '
        '"command_hint": string, '
        '"action_type": "edit"|"analyze"|"create", '
        '"create_action": string|null'
        "}\n"
        "If the request is vague (e.g. 'make it better'), set needs_clarification true and ask "
        "whether to change the selection or the whole document, and what kind of improvement. "
        "If there is a selection, prefer asking about selection vs whole document. "
        "command_hint should be one of: improve, shorten, expand, simplify, fix_grammar, "
        "rephrase, translate, change_tone, professional, summarize, main_ideas, keywords, "
        "create_summary, create_notes, create_outline, create_faq, custom.\n"
        f"Reply in the user locale: {locale}."
    )
    user = json.dumps(
        {
            "message": user_message,
            "has_selection": has_selection,
            "document_excerpt": document_excerpt[:4000],
        },
        ensure_ascii=False,
    )
    raw = await chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        base_url=ollama_url,
        model=model,
        format_json=True,
        temperature=0.1,
    )
    try:
        data = parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        data = {}
    data.setdefault("needs_clarification", True)
    data.setdefault(
        "question",
        "Should I apply this to the selected fragment or the whole document?",
    )
    data.setdefault("interpreted_scope", "selection" if has_selection else "document")
    data.setdefault("command_hint", "custom")
    data.setdefault("action_type", "edit")
    data.setdefault("create_action", None)
    return data


async def run_analyze_agent(
    *,
    command_id: str,
    document_text: str,
    custom_instruction: str | None,
    locale: str,
    ollama_url: str,
    model: str,
) -> str:
    instruction = PRESET_INSTRUCTIONS.get(command_id, PRESET_INSTRUCTIONS["analyze_text"])
    if custom_instruction:
        instruction = f"{instruction}\n\n{custom_instruction}"
    system = (
        f"You analyze documents. Respond in locale {locale}. "
        "Do not rewrite the source; return analysis only."
    )
    return await chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{instruction}\n\nDOCUMENT:\n{document_text[:12000]}"},
        ],
        base_url=ollama_url,
        model=model,
        temperature=0.3,
    )


async def generate_document_text(
    *,
    command_id: str,
    source_text: str,
    custom_instruction: str | None,
    locale: str,
    ollama_url: str,
    model: str,
) -> str:
    instruction = PRESET_INSTRUCTIONS.get(command_id, PRESET_INSTRUCTIONS["create_document"])
    if custom_instruction:
        instruction = f"{instruction}\n\n{custom_instruction}"
    system = (
        f"Create a new standalone document. Locale: {locale}. "
        "Return the document body only, no preamble."
    )
    return await chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{instruction}\n\nSOURCE:\n{source_text[:12000]}"},
        ],
        base_url=ollama_url,
        model=model,
        temperature=0.35,
    )


def suggested_title(command_id: str, source_title: str) -> str:
    labels = {
        "create_summary": "Summary",
        "create_notes": "Notes",
        "create_outline": "Outline",
        "create_faq": "FAQ",
        "summarize": "Summary",
        "main_ideas": "Main Ideas",
        "keywords": "Keywords",
    }
    suffix = labels.get(command_id, "AI")
    base = source_title or "Document"
    return f"{base} — {suffix}"


async def refine_style_profile(
    profile: dict[str, Any],
    accepted_before: str,
    accepted_after: str,
    ollama_url: str,
    model: str,
) -> dict[str, Any]:
    system = (
        "Infer the user's writing preferences from an accepted edit. "
        'Return JSON: {"sentence_length": "short|medium|long", "formality": "low|medium|high", '
        '"preferred_words": string[], "tone": string, "notes": string}'
    )
    user = f"BEFORE:\n{accepted_before}\n\nAFTER:\n{accepted_after}"
    raw = await chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        base_url=ollama_url,
        model=model,
        format_json=True,
        temperature=0.2,
    )
    try:
        delta = parse_json_response(raw)
        return {**profile, **delta}
    except (json.JSONDecodeError, ValueError):
        return profile


def merge_edited_span(full: str, start: int, end: int, new_span: str) -> str:
    if start < 0 or end > len(full) or start > end:
        raise ValueError("Invalid selection range")
    return full[:start] + new_span + full[end:]


def plain_text_to_html(text: str) -> str:
    paragraphs = re.split(r"\n\s*\n", text.strip())
    parts = []
    for p in paragraphs:
        if not p.strip():
            continue
        escaped = (
            p.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        parts.append(f"<p>{escaped}</p>")
    return "".join(parts) if parts else "<p></p>"
