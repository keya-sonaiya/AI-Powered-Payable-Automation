"""
Ollama Cloud client. The LLM is used for exactly two things — structuring
raw OCR text into JSON, and writing a plain-English audit explanation — and
NEVER makes the approve/exception/fraud decision; policy_engine.py already
decided by the time explain_decision() is called.

Corrected API (see PROGRESS.md): POST {OLLAMA_HOST}/api/chat with a
"messages" array, model "gpt-oss:120b" (no "-cloud" suffix — that suffix is
only for local `ollama run` invocations, not the hosted API).
"""
from __future__ import annotations

import asyncio
import json
import math
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings
from app.services import vector_store

_EMPTY_EXTRACTION: dict[str, Any] = {
    "invoice_number": None,
    "vendor_name": None,
    "po_number": None,
    "amount": None,
    "quantity": None,
    "unit_price": None,
    "invoice_date": None,
}

_EXTRACTION_SYSTEM_PROMPT = """You are an invoice data extraction engine. Given raw \
OCR text from an invoice, extract these fields and respond with STRICT JSON only \
(no prose, no markdown code fences):

{"invoice_number": string|null, "vendor_name": string|null, "po_number": string|null, \
"amount": number|null, "quantity": number|null, "unit_price": number|null, \
"invoice_date": string|null}

If a field cannot be determined from the text, use null. Never invent values."""

_EXPLANATION_SYSTEM_PROMPT = """You are writing a plain-English explanation for a \
finance auditor reviewing an accounts-payable automation decision. In 2-3 sentences, \
explain why the invoice received its decision, citing the specific policy clause \
provided and the concrete numbers (amounts, quantities, variances) that drove it. \
 The decision is already final — do not suggest or imply a different one. Treat the \
provided variance values and match-result numbers as authoritative facts. Never say \
there is "no amount variance" or "no quantity variance" when the corresponding \
provided variance is nonzero. A duplicate rule may determine the final decision, but \
that does not erase or change any other measured variance; mention those facts \
accurately if they are relevant."""

# A single backend worker otherwise starts one cloud request per concurrent
# /ingest request. Ollama Cloud returns 429 for that burst. This protects every
# caller (n8n, the dashboard, and direct API clients), even if a caller forgets
# to pace its own work.
_chat_semaphore = asyncio.Semaphore(settings.ollama_max_concurrency)


def _retry_delay(retry_after: str | None, attempt: int) -> float:
    """Return a bounded delay, preferring Ollama's Retry-After value when sent."""
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return settings.ollama_retry_delay_seconds * (2 ** attempt)


async def _chat(messages: list[dict], json_mode: bool = False) -> str:
    # Fail fast and clearly rather than sending an unauthenticated request
    # that Ollama Cloud will reject anyway — per API_CONTRACT.md, a broken
    # Ollama call should surface as a clean 502 with a message, never a raw
    # 500/stack trace to the caller.
    if not settings.ollama_api_key:
        raise HTTPException(
            status_code=502,
            detail=(
                "OLLAMA_API_KEY is not configured, so Ollama Cloud cannot be "
                "reached. Set OLLAMA_API_KEY in .env and restart the backend "
                "to enable invoice extraction and explanation."
            ),
        )

    payload: dict[str, Any] = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
    }
    if json_mode:
        payload["format"] = "json"

    headers = {"Authorization": f"Bearer {settings.ollama_api_key}"}

    for attempt in range(settings.ollama_max_retries + 1):
        try:
            async with _chat_semaphore:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{settings.ollama_host}/api/chat",
                        headers=headers,
                        json=payload,
                        timeout=60,
                    )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach Ollama Cloud at {settings.ollama_host}: {e}",
            ) from e

        if resp.status_code == 429:
            delay = _retry_delay(resp.headers.get("Retry-After"), attempt)
            if attempt < settings.ollama_max_retries:
                await asyncio.sleep(delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=(
                    "Ollama Cloud is rate-limiting requests after retries. "
                    "Retry the ingest shortly."
                ),
                headers={"Retry-After": str(math.ceil(delay))},
            )

        try:
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Ollama Cloud returned an error ({e.response.status_code}): "
                       f"{e.response.text[:300]}",
            ) from e
        break

    try:
        return data["message"]["content"]
    except (KeyError, TypeError) as e:
        raise HTTPException(
            status_code=502,
            detail="Ollama Cloud returned an unexpected response shape "
                   "(no message.content field).",
        ) from e


async def extract_invoice_fields(raw_ocr_text: str) -> dict[str, Any]:
    """Structures raw OCR text into JSON. LLM does extraction ONLY, not decisions."""
    content = await _chat(
        [
            {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": raw_ocr_text},
        ],
        json_mode=True,
    )
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return dict(_EMPTY_EXTRACTION)

    return {**_EMPTY_EXTRACTION, **parsed}


async def explain_decision(invoice: dict, match_result: dict, decision: dict) -> str:
    """
    Plain-English audit explanation, grounded in the actual policy text via
    vector_store.get_relevant_clauses() — the retrieval step the original
    spec diagrammed but never wired up.
    """
    clauses = vector_store.get_relevant_clauses(decision["rule_applied"], k=1)
    policy_text = clauses[0] if clauses else "(no matching policy clause found)"

    user_prompt = f"""Decision: {decision['decision']}
Rule applied: {decision['rule_applied']}
Amount variance: {decision.get('amount_variance_pct')}
Quantity variance: {decision.get('quantity_variance_pct')}

Relevant policy clause:
\"\"\"
{policy_text}
\"\"\"

Invoice data: {json.dumps(invoice, default=str)}
Match result (PO / receipt): {json.dumps(match_result, default=str)}"""

    return await _chat(
        [
            {"role": "system", "content": _EXPLANATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
