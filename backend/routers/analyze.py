"""
routers/analyze.py
──────────────────
POST /analyze — runs Content Understanding extraction on an uploaded document,
                then indexes the result into Azure AI Search.
"""

from fastapi import APIRouter, HTTPException
from backend.services import blob_service, content_understanding, search_service
from backend.models.schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("", response_model=AnalyzeResponse)
async def analyze_document(request: AnalyzeRequest):
    """
    Analyze a document using Azure Content Understanding.

    Steps:
      1. Download the document from Blob Storage.
      2. Submit to Content Understanding for field extraction.
      3. Index the extracted text into Azure AI Search.
      4. Return extracted fields + raw content.
    """
    # ── 1. Download document from Blob ────────────────────────
    try:
        file_bytes = await blob_service.download_document(request.doc_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {request.doc_id}. Error: {str(e)}",
        )

    # ── 2. Extract with Content Understanding ─────────────────
    try:
        extraction = await content_understanding.analyze_document(
            doc_id=request.doc_id,
            file_bytes=file_bytes,
            filename=request.doc_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Content Understanding extraction failed: {str(e)}",
        )

    # ── 3. Index into AI Search ───────────────────────────────
    indexed = False
    try:
        search_service.create_index_if_not_exists()
        chunks_count = await search_service.index_document(
            doc_id=request.doc_id,
            filename=request.doc_id,
            raw_content=extraction["raw_content"],
        )
        indexed = chunks_count > 0
    except Exception as e:
        # Non-fatal: log but don't fail the whole request
        print(f"[WARN] Search indexing failed for {request.doc_id}: {e}")

    from backend.core.config import get_settings
    settings = get_settings()

    return AnalyzeResponse(
        doc_id=request.doc_id,
        analyzer_id=settings.azure_cu_analyzer_id,
        fields=extraction["fields"],
        raw_content=extraction["raw_content"],
        indexed=indexed,
    )
