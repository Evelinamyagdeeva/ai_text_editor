from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings

class LLMError(Exception):
    pass


OllamaError = LLMError

_TIMEOUT = httpx.Timeout(180.0, connect=15.0)


def _http_error_message(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return (
            "Таймаут при обращении к Polza (polza.ai не ответил вовремя). "
            "Проверьте интернет, VPN или откройте polza.ai в браузере."
        )
    if isinstance(exc, httpx.HTTPStatusError):
        body = (exc.response.text or "").strip()
        if body:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    err = parsed.get("error") or parsed.get("message") or parsed.get("detail")
                    if isinstance(err, dict):
                        err = err.get("message") or str(err)
                    if err:
                        body = str(err)
            except json.JSONDecodeError:
                body = body[:400]
        else:
            body = exc.response.reason_phrase or "unknown error"
        return f"Polza HTTP {exc.response.status_code}: {body}"
    msg = str(exc).strip()
    return msg or f"{type(exc).__name__} (сеть или SSL)"


async def chat(
    messages: list[dict[str, str]],
    *,
    base_url: str | None = None,
    model: str | None = None,
    format_json: bool = False,
    temperature: float = 0.3,
) -> str:
    root = (base_url or settings.polza_ai_base_url).rstrip("/")
    url = root + "/chat/completions"
    model_name = model or settings.polza_ai_model_name
    api_key = settings.polza_ai_api_key
    if not api_key:
        raise LLMError("POLZA_AI_API_KEY is missing in .env")

    body: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
    }
    if format_json:
        body["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, trust_env=False) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise LLMError(f"Polza request failed: {_http_error_message(e)}") from e
    except json.JSONDecodeError as e:
        raise LLMError("Polza returned invalid JSON") from e

    choices = data.get("choices") or []
    if not choices:
        raise LLMError("Empty response from Polza")
    content = ((choices[0].get("message") or {}).get("content")) or ""
    if not content:
        raise LLMError("Empty response from Polza")
    return str(content).strip()


async def check_connection(base_url: str | None = None) -> dict[str, Any]:
    if not settings.polza_ai_api_key:
        return {"ok": False, "error": "POLZA_AI_API_KEY is missing"}
    root = (base_url or settings.polza_ai_base_url).rstrip("/")
    url = root + "/models"
    headers = {"Authorization": f"Bearer {settings.polza_ai_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=5.0), trust_env=False) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return {"ok": True, "models": data.get("data", [])}
    except httpx.HTTPError as e:
        return {"ok": False, "error": _http_error_message(e)}


def parse_json_response(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
