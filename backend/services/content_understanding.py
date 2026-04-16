"""
services/content_understanding.py
──────────────────────────────────
Extracts structured fields and full text from documents using
Azure AI Content Understanding (part of Azure AI Foundry).

Content Understanding goes beyond Document Intelligence —
it supports custom analyzers, multimodal content, and
layout-aware field extraction configured in AI Foundry Studio.

Auth: DefaultAzureCredential (keyless) by default.
      Falls back to API key if AZURE_CU_API_KEY is set.

Docs: https://learn.microsoft.com/azure/ai-services/content-understanding/
"""

from __future__ import annotations

import time
import httpx

from backend.core.config import get_settings
from backend.core.auth import get_credential, get_cu_api_key
from backend.models.schemas import ExtractedField


# ── Internal helpers ──────────────────────────────────────────

def _get_headers() -> dict[str, str]:
    """Build auth headers — API key if available, else bearer token."""
    api_key = get_cu_api_key()
    if api_key:
        return {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/json",
        }

    # Keyless: get a fresh bearer token from DefaultAzureCredential
    credential = get_credential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    return {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }


# ── Public API ────────────────────────────────────────────────

async def analyze_document(doc_id: str, file_bytes: bytes, filename: str) -> dict:
    """
    Submit a document to Azure Content Understanding for field extraction.

    Returns:
        {
            "fields": list[ExtractedField],
            "raw_content": str,
        }
    """
    settings = get_settings()
    headers = _get_headers()

    # ── Step 1: Submit the document for analysis ──────────────
    import base64
    encoded = base64.b64encode(file_bytes).decode("utf-8")

    submit_url = (
        f"{settings.azure_cu_endpoint}/contentunderstanding/analyzers"
        f"/{settings.azure_cu_analyzer_id}:analyze"
        f"?api-version=2024-12-01-preview"
    )

    payload = {
        "url": None,
        "base64Source": encoded,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(submit_url, headers=headers, json=payload)
        resp.raise_for_status()

        # Check if result is synchronous or async (operation-based)
        if resp.status_code == 200:
            result = resp.json()
        else:
            # 202 Accepted — poll the operation
            operation_url = resp.headers.get("Operation-Location")
            if not operation_url:
                raise ValueError("No Operation-Location header in CU response")
            result = await _poll_operation(client, operation_url, headers)

    return _parse_result(result)


async def _poll_operation(
    client: httpx.AsyncClient,
    operation_url: str,
    headers: dict,
    max_wait_seconds: int = 120,
    poll_interval: float = 2.0,
) -> dict:
    """Poll an async Content Understanding operation until it completes."""
    elapsed = 0.0
    while elapsed < max_wait_seconds:
        resp = await client.get(operation_url, headers=headers)
        resp.raise_for_status()
        body = resp.json()

        status = body.get("status", "").lower()
        if status == "succeeded":
            return body
        elif status in ("failed", "canceled"):
            error = body.get("error", {})
            raise RuntimeError(
                f"Content Understanding operation {status}: {error.get('message', 'unknown error')}"
            )

        await _async_sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(
        f"Content Understanding operation did not complete within {max_wait_seconds}s"
    )


def _parse_result(result: dict) -> dict:
    """
    Parse the Content Understanding response into our internal format.
    Handles both the direct result shape and the operation result shape.
    """
    # Navigate to the analyzer result
    analyze_result = (
        result.get("result", result)
              .get("analyzeResult", result.get("analyzeResult", {}))
    )

    fields: list[ExtractedField] = []
    raw_content = ""

    # ── Extract structured fields ─────────────────────────────
    documents = analyze_result.get("documents", [])
    for doc in documents:
        for field_name, field_data in doc.get("fields", {}).items():
            fields.append(
                ExtractedField(
                    name=field_name,
                    value=field_data.get("valueString")
                          or field_data.get("content")
                          or field_data.get("value"),
                    confidence=field_data.get("confidence"),
                )
            )

    # ── Extract raw text content ──────────────────────────────
    pages = analyze_result.get("pages", [])
    page_texts = []
    for page in pages:
        page_lines = [line.get("content", "") for line in page.get("lines", [])]
        page_texts.append("\n".join(page_lines))
    raw_content = "\n\n".join(page_texts)

    # Fallback: top-level content field
    if not raw_content:
        raw_content = analyze_result.get("content", "")

    return {
        "fields": fields,
        "raw_content": raw_content,
    }


async def _async_sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)
