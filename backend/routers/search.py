"""
routers/search.py
─────────────────
GET /search — semantic + keyword search over indexed documents.
"""

from fastapi import APIRouter, HTTPException, Query
from backend.services import search_service
from backend.models.schemas import SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    top: int = Query(default=5, ge=1, le=20, description="Number of results"),
    semantic: bool = Query(default=True, description="Use semantic ranker"),
    doc_id: str | None = Query(default=None, description="Filter to specific document"),
):
    """
    Search across all indexed documents.

    - Uses Azure AI Search semantic ranker for best relevance.
    - Returns matching chunks with highlights.
    - Optionally filter to a specific doc_id.
    """
    try:
        results = await search_service.search_documents(
            query=q,
            top=top,
            semantic=semantic,
            doc_id_filter=doc_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Search failed: {str(e)}",
        )

    return SearchResponse(
        query=q,
        results=results,
        total=len(results),
    )
