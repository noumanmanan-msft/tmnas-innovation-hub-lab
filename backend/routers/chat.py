"""
routers/chat.py
───────────────
POST /chat — RAG-grounded conversational Q&A over documents.
"""

from fastapi import APIRouter, HTTPException
from backend.services import openai_service
from backend.models.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with your documents using GPT-4o + RAG.

    - Retrieves relevant chunks from Azure AI Search.
    - Grounds GPT-4o response in document context.
    - Returns the reply and the source chunks used.
    
    Set use_rag=false to skip retrieval (direct GPT-4o, no grounding).
    Set doc_id to restrict context to a single document.
    """
    try:
        result = await openai_service.chat(
            messages=request.messages,
            doc_id=request.doc_id,
            use_rag=request.use_rag,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Chat completion failed: {str(e)}",
        )

    return ChatResponse(**result)


@router.post("/analyze-text", tags=["chat"])
async def analyze_text(payload: dict):
    """
    One-shot: run GPT-4o document analysis on raw text.
    Useful for quick demos without the full upload→analyze pipeline.

    Body: { "content": "...document text..." }
    """
    content = payload.get("content", "")
    if not content:
        raise HTTPException(status_code=422, detail="content field is required")

    try:
        analysis = await openai_service.analyze_document_with_llm(content)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {str(e)}")

    return {"analysis": analysis}
