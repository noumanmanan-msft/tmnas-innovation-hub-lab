"""
services/search_service.py
──────────────────────────
Indexes extracted document content and runs semantic/vector search
using Azure AI Search.

Auth: DefaultAzureCredential (keyless) by default.
      Falls back to API key if AZURE_SEARCH_API_KEY is set.

Docs: https://learn.microsoft.com/azure/search/
"""

from __future__ import annotations

import textwrap
import uuid
import re

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
)
from azure.search.documents.models import QueryType

from backend.core.config import get_settings
from backend.core.auth import get_credential, get_search_api_key
from backend.models.schemas import SearchResult


CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 100     # overlap between chunks


# ── Auth helpers ──────────────────────────────────────────────

def _get_credential():
    """Return API key credential if available, else DefaultAzureCredential."""
    return get_search_api_key() or get_credential()


# ── Index management ──────────────────────────────────────────

def get_index_client() -> SearchIndexClient:
    settings = get_settings()
    return SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=_get_credential(),
    )


def get_search_client() -> SearchClient:
    settings = get_settings()
    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index_name,
        credential=_get_credential(),
    )


def create_index_if_not_exists() -> bool:
    """
    Create the search index if it doesn't exist.
    Returns True if created, False if it already existed.

    Call this from scripts/create_search_index.py or on app startup.
    """
    settings = get_settings()
    index_client = get_index_client()

    existing = list(index_client.list_index_names())
    if settings.azure_search_index_name in existing:
        return False

    index = SearchIndex(
        name=settings.azure_search_index_name,
        fields=[
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
            ),
            SimpleField(
                name="doc_id",
                type=SearchFieldDataType.String,
                filterable=True,
            ),
            SimpleField(
                name="filename",
                type=SearchFieldDataType.String,
                filterable=True,
                retrievable=True,
            ),
            SearchableField(
                name="chunk",
                type=SearchFieldDataType.String,
                analyzer_name="en.microsoft",
            ),
            SimpleField(
                name="chunk_index",
                type=SearchFieldDataType.Int32,
                retrievable=True,
            ),
        ],
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="default",
                    prioritized_fields=SemanticPrioritizedFields(
                        content_fields=[SemanticField(field_name="chunk")]
                    ),
                )
            ],
            default_configuration_name="default",
        ),
    )

    index_client.create_index(index)
    return True


# ── Indexing ──────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks for indexing.
    Simple character-based chunking — extend with sentence-aware
    splitting (e.g. spaCy, nltk) for production.
    """
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap  # slide with overlap
    return chunks


def _build_search_doc_key(doc_id: str, chunk_index: int) -> str:
    # Azure AI Search keys only allow letters, digits, _, -, =
    normalized = re.sub(r"[^A-Za-z0-9_\-=]", "-", doc_id)
    return f"{normalized}_{chunk_index}"


async def index_document(doc_id: str, filename: str, raw_content: str) -> int:
    """
    Chunk raw_content and upload all chunks to the search index.
    Returns the number of chunks indexed.
    """
    chunks = chunk_text(raw_content)
    if not chunks:
        return 0

    documents = [
        {
            "id": _build_search_doc_key(doc_id, i),
            "doc_id": doc_id,
            "filename": filename,
            "chunk": chunk,
            "chunk_index": i,
        }
        for i, chunk in enumerate(chunks)
    ]

    search_client = get_search_client()
    search_client.upload_documents(documents=documents)
    return len(chunks)


# ── Search ────────────────────────────────────────────────────

async def search_documents(
    query: str,
    top: int = 5,
    semantic: bool = True,
    doc_id_filter: str | None = None,
) -> list[SearchResult]:
    """
    Search the index for relevant chunks.

    Args:
        query: Natural language search query.
        top: Number of results to return.
        semantic: Use semantic ranker (requires Basic tier or above).
        doc_id_filter: Restrict search to a specific document.

    Returns:
        List of SearchResult objects sorted by relevance.
    """
    search_client = get_search_client()

    filter_expr = f"doc_id eq '{doc_id_filter}'" if doc_id_filter else None

    kwargs: dict = {
        "search_text": query,
        "top": top,
        "filter": filter_expr,
        "highlight_fields": "chunk",
        "highlight_pre_tag": "<mark>",
        "highlight_post_tag": "</mark>",
    }

    if semantic:
        kwargs["query_type"] = QueryType.SEMANTIC
        kwargs["semantic_configuration_name"] = "default"
        kwargs["query_caption"] = "extractive"

    results = []
    for r in search_client.search(**kwargs):
        highlights = []
        if r.get("@search.highlights"):
            highlights = r["@search.highlights"].get("chunk", [])

        results.append(
            SearchResult(
                doc_id=r["doc_id"],
                filename=r["filename"],
                score=r.get("@search.score", 0.0),
                chunk=r["chunk"],
                highlights=highlights,
            )
        )

    return results
