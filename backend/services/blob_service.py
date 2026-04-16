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

from azure.core.exceptions import HttpResponseError
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceExistsError

from backend.core.config import get_settings
from backend.core.auth import get_credential


def _get_keyless_client() -> BlobServiceClient:
    settings = get_settings()

    return BlobServiceClient(
        account_url=settings.blob_account_url,
        credential=get_credential(),
    )


def _get_client() -> BlobServiceClient:
    settings = get_settings()

    # Prefer connection string if provided (API key fallback)
    if settings.azure_storage_connection_string:
        return BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )

    # Keyless: DefaultAzureCredential
    return _get_keyless_client()


def _is_shared_key_auth_error(exc: Exception) -> bool:
    message = str(exc)
    return "KeyBasedAuthenticationNotPermitted" in message


def _with_storage_fallback(action):
    """Run storage action and retry with keyless auth when shared-key auth is blocked."""
    try:
        return action(_get_client())
    except HttpResponseError as exc:
        if not _is_shared_key_auth_error(exc):
            raise
    except Exception as exc:
        if not _is_shared_key_auth_error(exc):
            raise

    return action(_get_keyless_client())


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

    # Generate a unique blob name to avoid collisions
    ext = Path(filename).suffix
    doc_id = f"{uuid.uuid4()}{ext}"

    content_type = _infer_content_type(ext)

    def _upload(client: BlobServiceClient) -> dict:
        _ensure_container(client, settings.azure_storage_container_name)

        blob_client = client.get_blob_client(
            container=settings.azure_storage_container_name,
            blob=doc_id,
        )
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

    return _with_storage_fallback(_upload)


async def download_document(doc_id: str) -> bytes:
    """Download a document from Blob Storage by doc_id."""
    settings = get_settings()

    def _download(client: BlobServiceClient) -> bytes:
        blob_client = client.get_blob_client(
            container=settings.azure_storage_container_name,
            blob=doc_id,
        )
        stream = blob_client.download_blob()
        return stream.readall()

    return _with_storage_fallback(_download)


async def list_documents() -> list[dict]:
    """List all documents in the container."""
    settings = get_settings()

    try:
        def _list(client: BlobServiceClient) -> list[dict]:
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

        return _with_storage_fallback(_list)
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
