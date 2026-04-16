"""
models/schemas.py
─────────────────
Pydantic models for all API request and response payloads.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Upload ────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    doc_id: str = Field(..., description="Unique document ID (blob name)")
    filename: str
    blob_url: str
    size_bytes: int
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


# ── Analyze (Content Understanding) ──────────────────────────

class AnalyzeRequest(BaseModel):
    doc_id: str = Field(..., description="Document ID returned from /upload")


class ExtractedField(BaseModel):
    name: str
    value: Any
    confidence: float | None = None


class AnalyzeResponse(BaseModel):
    doc_id: str
    analyzer_id: str
    fields: list[ExtractedField]
    raw_content: str = Field(default="", description="Full extracted text")
    indexed: bool = Field(default=False, description="Whether doc was added to AI Search")


# ── Search ────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top: int = Field(default=5, ge=1, le=20)
    semantic: bool = Field(default=True, description="Use semantic ranker")


class SearchResult(BaseModel):
    doc_id: str
    filename: str
    score: float
    chunk: str
    highlights: list[str] = []


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


# ── Chat ──────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    doc_id: str | None = Field(
        default=None,
        description="If set, grounds the conversation to this specific document."
    )
    use_rag: bool = Field(
        default=True,
        description="If True, retrieves relevant chunks from AI Search before calling GPT-4o."
    )


class ChatResponse(BaseModel):
    reply: str
    sources: list[SearchResult] = []
    prompt_tokens: int = 0
    completion_tokens: int = 0
