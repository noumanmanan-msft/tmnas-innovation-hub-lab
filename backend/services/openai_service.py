"""
services/openai_service.py
──────────────────────────
GPT-4o chat and document analysis via Azure OpenAI.
Supports RAG: retrieves relevant chunks from AI Search before
each generation call to ground responses in your documents.

Auth: DefaultAzureCredential (keyless) by default.
      Falls back to API key if AZURE_OPENAI_API_KEY is set.

Docs: https://learn.microsoft.com/azure/ai-services/openai/
"""

from __future__ import annotations

from openai import AsyncAzureOpenAI
from azure.identity import get_bearer_token_provider

from backend.core.config import get_settings
from backend.core.auth import get_credential, get_openai_api_key
from backend.models.schemas import ChatMessage, SearchResult
from backend.services import search_service


# ── System prompts ────────────────────────────────────────────

SYSTEM_PROMPT_BASE = """You are an expert document reviewer assistant.
Your job is to help users understand, extract key information from, and 
answer questions about documents.

Be precise, cite specific sections when possible, and flag any ambiguous 
or potentially risky clauses in legal or contractual documents."""

SYSTEM_PROMPT_WITH_CONTEXT = SYSTEM_PROMPT_BASE + """

You have been provided with relevant excerpts from the user's documents 
as CONTEXT. Always ground your answers in this context. If the context 
does not contain enough information to answer, say so clearly rather 
than speculating.

CONTEXT:
{context}
"""

ANALYSIS_PROMPT = """Analyze the following document and provide:
1. **Summary** — A 2-3 sentence overview of the document's purpose.
2. **Key Parties** — Any named individuals, companies, or entities.
3. **Critical Dates** — Deadlines, effective dates, expiration dates.
4. **Key Obligations** — What each party is required to do.
5. **Risks / Red Flags** — Unusual clauses, missing terms, or potential issues.
6. **Recommended Actions** — What the reviewer should do next.

Document content:
{content}
"""


# ── Client factory ────────────────────────────────────────────

def _get_client() -> AsyncAzureOpenAI:
    settings = get_settings()
    api_key = get_openai_api_key()

    if api_key:
        # API key mode
        return AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=api_key,
            api_version=settings.azure_openai_api_version,
        )

    # Keyless mode: use DefaultAzureCredential bearer token provider
    token_provider = get_bearer_token_provider(
        get_credential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_ad_token_provider=token_provider,
        api_version=settings.azure_openai_api_version,
    )


# ── Public API ────────────────────────────────────────────────

async def chat(
    messages: list[ChatMessage],
    doc_id: str | None = None,
    use_rag: bool = True,
) -> dict:
    """
    Run a RAG-grounded or direct chat completion.

    Args:
        messages: Conversation history (user + assistant turns).
        doc_id: If set, restricts RAG retrieval to this document.
        use_rag: Whether to retrieve context from AI Search.

    Returns:
        {"reply": str, "sources": list[SearchResult], "prompt_tokens": int, "completion_tokens": int}
    """
    settings = get_settings()
    client = _get_client()

    sources: list[SearchResult] = []
    system_content = SYSTEM_PROMPT_BASE

    # ── RAG: retrieve relevant chunks ────────────────────────
    if use_rag:
        last_user_msg = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        if last_user_msg:
            sources = await search_service.search_documents(
                query=last_user_msg,
                top=5,
                semantic=True,
                doc_id_filter=doc_id,
            )

        if sources:
            context_text = "\n\n---\n\n".join(
                f"[{s.filename}, chunk {i+1}]\n{s.chunk}"
                for i, s in enumerate(sources)
            )
            system_content = SYSTEM_PROMPT_WITH_CONTEXT.format(context=context_text)

    # ── Build messages for API call ───────────────────────────
    api_messages = [{"role": "system", "content": system_content}]
    api_messages += [{"role": m.role, "content": m.content} for m in messages]

    # ── Call GPT-4o ───────────────────────────────────────────
    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=api_messages,
        temperature=0.1,        # low temp for factual doc review
        max_tokens=2000,
    )

    reply = response.choices[0].message.content or ""
    usage = response.usage

    return {
        "reply": reply,
        "sources": sources,
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
    }


async def analyze_document_with_llm(raw_content: str) -> str:
    """
    Run a one-shot document analysis with GPT-4o.
    Returns a structured markdown analysis string.
    """
    settings = get_settings()
    client = _get_client()

    prompt = ANALYSIS_PROMPT.format(content=raw_content[:8000])  # token safety

    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_BASE},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )

    return response.choices[0].message.content or ""
