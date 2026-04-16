"""
core/auth.py
────────────
Centralised credential management.

Strategy (in priority order):
  1. DefaultAzureCredential  — picks up `az login`, Managed Identity,
                               Workload Identity, env vars automatically.
  2. API key fallback         — only used per-service when an explicit key
                               is set in .env (useful during workshops where
                               managed identity is not yet configured).

Import `get_credential()` everywhere you need an Azure credential.
"""

from functools import lru_cache

from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential

from backend.core.config import get_settings


@lru_cache
def get_credential() -> DefaultAzureCredential:
    """
    Returns a cached DefaultAzureCredential.

    This handles:
      • Local development  → az login
      • Azure-hosted       → Managed Identity / Workload Identity
      • CI/CD              → AZURE_CLIENT_ID / AZURE_CLIENT_SECRET env vars

    Note: credential is cached at process level — safe for FastAPI.
    """
    return DefaultAzureCredential(
        # Exclude interactive browser prompt to avoid blocking in server context.
        # Remove this exclusion if you want browser-based fallback locally.
        exclude_interactive_browser_credential=True,
        # Optional: speed up credential chain by excluding what you know is absent.
        # exclude_visual_studio_code_credential=True,
    )


def get_openai_api_key() -> str | None:
    """Returns OpenAI API key if configured, else None (use keyless)."""
    settings = get_settings()
    return settings.azure_openai_api_key or None


def get_search_api_key() -> AzureKeyCredential | None:
    """Returns Search AzureKeyCredential if configured, else None (use keyless)."""
    settings = get_settings()
    if settings.azure_search_api_key:
        return AzureKeyCredential(settings.azure_search_api_key)
    return None


def get_cu_api_key() -> str | None:
    """Returns Content Understanding API key if configured, else None (use keyless)."""
    settings = get_settings()
    return settings.azure_cu_api_key or None
