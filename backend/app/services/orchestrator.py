from __future__ import annotations

from typing import Any

from app.commands import PRESET_INSTRUCTIONS
from app.config import settings
from app.services import agents
from app.services.diff_service import word_diff
from app.services.metrics import compute_metrics


async def run_edit_pipeline(
    *,
    full_text: str,
    selection_start: int | None,
    selection_end: int | None,
    command_id: str,
    custom_instruction: str | None,
    memory: dict[str, Any],
    style_profile: dict[str, Any],
    locale: str,
    ollama_url: str | None,
    model: str | None,
    run_fact_check: bool = True,
) -> dict[str, Any]:
    url = ollama_url or settings.polza_ai_base_url
    model_name = model or settings.polza_ai_model_name

    if selection_start is not None and selection_end is not None:
        target = full_text[selection_start:selection_end]
        whole_for_context = full_text
    else:
        target = full_text
        selection_start = 0
        selection_end = len(full_text)
        whole_for_context = full_text

    instruction = PRESET_INSTRUCTIONS.get(command_id, PRESET_INSTRUCTIONS["custom"])
    if custom_instruction:
        instruction = f"{instruction}\n\n{custom_instruction}"

    edited_target = await agents.run_edit_agent(
        full_document=whole_for_context,
        target_text=target,
        command_id=command_id,
        custom_instruction=custom_instruction,
        memory=memory,
        style_profile=style_profile,
        locale=locale,
        ollama_url=url,
        model=model_name,
    )

    critic = await agents.run_critic_agent(
        original_target=target,
        edited_target=edited_target,
        instruction=instruction,
        ollama_url=url,
        model=model_name,
    )

    retries = 0
    while not critic.get("pass") and retries < settings.critic_max_retries:
        retry_prompt = critic.get("retry_prompt") or "; ".join(critic.get("issues") or [])
        edited_target = await agents.run_edit_agent(
            full_document=whole_for_context,
            target_text=target,
            command_id=command_id,
            custom_instruction=custom_instruction,
            memory=memory,
            style_profile=style_profile,
            locale=locale,
            ollama_url=url,
            model=model_name,
            retry_hint=retry_prompt,
        )
        critic = await agents.run_critic_agent(
            original_target=target,
            edited_target=edited_target,
            instruction=instruction,
            ollama_url=url,
            model=model_name,
        )
        retries += 1

    new_full = agents.merge_edited_span(full_text, selection_start, selection_end, edited_target)

    metrics_before = compute_metrics(target if len(target) < len(full_text) else full_text)
    metrics_after = compute_metrics(edited_target if len(target) < len(full_text) else new_full)

    claims: list[dict[str, str]] = []
    if run_fact_check:
        claims = await agents.extract_fact_claims(edited_target, url, model_name)

    return {
        "original_target": target,
        "edited_target": edited_target,
        "proposed_full_text": new_full,
        "selection_start": selection_start,
        "selection_end": selection_end,
        "diff": [{"kind": c.kind, "text": c.text} for c in word_diff(target, edited_target)],
        "critic": critic,
        "metrics_before": metrics_before.__dict__,
        "metrics_after": metrics_after.__dict__,
        "fact_claims": claims,
        "command_id": command_id,
    }
