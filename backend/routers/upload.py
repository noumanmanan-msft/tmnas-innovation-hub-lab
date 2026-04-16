"""
routers/upload.py
─────────────────
POST /upload       — accepts a document file and stores it in Azure Blob Storage.
GET  /upload/list  — lists all documents in the container.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.services import blob_service
from backend.models.schemas import UploadResponse

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "image/png",
    "image/jpeg",
}

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document to Azure Blob Storage.

    - Accepts: PDF, TXT, DOCX, PNG, JPEG (max 20 MB)
    - Returns: doc_id to use in /analyze and /chat endpoints
    """
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed: {', '.join(ALLOWED_TYPES)}",
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB.",
        )

    try:
        result = await blob_service.upload_document(
            file_bytes=file_bytes,
            filename=file.filename or "unnamed",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    return UploadResponse(**result)


@router.get("/list")
async def list_documents():
    """List all documents stored in Azure Blob Storage."""
    try:
        return await blob_service.list_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not list documents: {str(e)}")
