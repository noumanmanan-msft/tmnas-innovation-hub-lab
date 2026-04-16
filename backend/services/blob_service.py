"""
services/blob_service.py
────────────────────────
Handles document upload / download / listing with Azure Blob Storage.

Auth: DefaultAzureCredential (keyless) by default.
      Falls back to connection string if AZURE_STORAGE_CONNECTION_STRING is set.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceExistsError

from backend.core.config import get_settings
from backend.core.auth import get_credential


def _get_client() -> BlobServiceClient:
    settings = get_settings()

    # Prefer connection string if provided (API key fallback)
    if settings.azure_storage_connection_string:
        return BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )

    # Keyless: DefaultAzureCredential
    return BlobServiceClient(
        account_url=settings.blob_account_url,
        credential=get_credential(),
    )


def _ensure_container(client: BlobServiceClient, container_name: str) -> None:
    """Create container if it doesn't exist (idempotent)."""
    try:
        client.create_container(container_name)
    except ResourceExistsError:
        pass


async def upload_document(file_bytes: bytes, filename: str) -> dict:
    """
    Upload a document to Blob Storage.

    Returns a dict with doc_id, blob_url, and size.
    """
    settings = get_settings()
    client = _get_client()
    _ensure_container(client, settings.azure_storage_container_name)

    # Generate a unique blob name to avoid collisions
    ext = Path(filename).suffix
    doc_id = f"{uuid.uuid4()}{ext}"

    blob_client = client.get_blob_client(
        container=settings.azure_storage_container_name,
        blob=doc_id,
    )

    content_type = _infer_content_type(ext)
    blob_client.upload_blob(
        data=file_bytes,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
        metadata={"original_filename": filename},
    )

    return {
        "doc_id": doc_id,
        "filename": filename,
        "blob_url": blob_client.url,
        "size_bytes": len(file_bytes),
    }


async def download_document(doc_id: str) -> bytes:
    """Download a document from Blob Storage by doc_id."""
    settings = get_settings()
    client = _get_client()

    blob_client = client.get_blob_client(
        container=settings.azure_storage_container_name,
        blob=doc_id,
    )
    stream = blob_client.download_blob()
    return stream.readall()


async def list_documents() -> list[dict]:
    """List all documents in the container."""
    settings = get_settings()
    client = _get_client()

    try:
        container_client = client.get_container_client(
            settings.azure_storage_container_name
        )
        blobs = []
        for blob in container_client.list_blobs(include=["metadata"]):
            blobs.append({
                "doc_id": blob.name,
                "filename": blob.metadata.get("original_filename", blob.name)
                            if blob.metadata else blob.name,
                "size_bytes": blob.size,
                "last_modified": blob.last_modified,
            })
        return blobs
    except Exception:
        return []


def _infer_content_type(ext: str) -> str:
    mapping = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    return mapping.get(ext.lower(), "application/octet-stream")
