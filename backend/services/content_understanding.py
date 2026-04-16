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

import base64
import mimetypes
import time
import httpx

from backend.core.config import get_settings
from backend.core.auth import get_credential, get_cu_api_key
from backend.models.schemas import ExtractedField


CU_API_VERSION = "2025-11-01"


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
    base_endpoint = settings.azure_cu_endpoint.rstrip("/")

    # ── Step 1: Submit the document for analysis ──────────────
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    submit_url = (
        f"{base_endpoint}/contentunderstanding/analyzers"
        f"/{settings.azure_cu_analyzer_id}:analyze"
        f"?api-version={CU_API_VERSION}"
    )

    payload = {
        "inputs": [
            {
                "name": filename,
                "data": encoded,
                "mimeType": mime_type,
            }
        ],
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
    operation_result = result.get("result", result)

    fields: list[ExtractedField] = []
    contents = operation_result.get("contents", [])

    if contents:
        for content in contents:
            for field_name, field_data in content.get("fields", {}).items():
                fields.append(
                    ExtractedField(
                        name=field_name,
                        value=_field_value(field_data),
                        confidence=field_data.get("confidence"),
                    )
                )

        raw_content = "\n\n".join(
            content.get("markdown", "") for content in contents if content.get("markdown")
        )

        if not raw_content:
            paragraphs = []
            for content in contents:
                paragraphs.extend(
                    paragraph.get("content", "")
                    for paragraph in content.get("paragraphs", [])
                    if paragraph.get("content")
                )
            raw_content = "\n\n".join(paragraphs)
    else:
        # Legacy fallback for older response shapes.
        analyze_result = operation_result.get(
            "analyzeResult",
            result.get("analyzeResult", {}),
        )
        documents = analyze_result.get("documents", [])
        for doc in documents:
            for field_name, field_data in doc.get("fields", {}).items():
                fields.append(
                    ExtractedField(
                        name=field_name,
                        value=_field_value(field_data),
                        confidence=field_data.get("confidence"),
                    )
                )

        pages = analyze_result.get("pages", [])
        page_texts = []
        for page in pages:
            page_lines = [line.get("content", "") for line in page.get("lines", [])]
            page_texts.append("\n".join(page_lines))
        raw_content = "\n\n".join(page_texts) or analyze_result.get("content", "")

    return {
        "fields": fields,
        "raw_content": raw_content,
    }


def _field_value(field_data: dict) -> object:
    field_type = field_data.get("type")

    if field_type == "string":
        return field_data.get("valueString") or field_data.get("content")
    if field_type == "date":
        return field_data.get("valueDate")
    if field_type == "time":
        return field_data.get("valueTime")
    if field_type == "number":
        return field_data.get("valueNumber")
    if field_type == "integer":
        return field_data.get("valueInteger")
    if field_type == "boolean":
        return field_data.get("valueBoolean")
    if field_type == "json":
        return field_data.get("valueJson")
    if field_type == "array":
        return [_field_value(item) for item in field_data.get("valueArray", [])]
    if field_type == "object":
        return {
            key: _field_value(value)
            for key, value in field_data.get("valueObject", {}).items()
        }

    return (
        field_data.get("valueString")
        or field_data.get("content")
        or field_data.get("value")
        or field_data.get("valueJson")
    )


async def _async_sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)
