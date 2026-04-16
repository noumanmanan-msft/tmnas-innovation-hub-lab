"""
core/config.py
──────────────
Loads all configuration from environment variables / .env file.
Uses pydantic-settings for validation and type safety.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Azure Subscription ────────────────────────────────────
    azure_subscription_id: str = ""
    azure_resource_group: str = ""

    # ── Azure AI Foundry Project ──────────────────────────────
    azure_ai_project_name: str = ""
    azure_ai_project_endpoint: str = ""

    # ── Azure OpenAI ──────────────────────────────────────────
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_api_key: str = ""          # Optional: leave blank for keyless

    # ── Azure AI Search ───────────────────────────────────────
    azure_search_endpoint: str = ""
    azure_search_index_name: str = "doc-review-index"
    azure_search_api_key: str = ""          # Optional: leave blank for keyless

    # ── Azure Blob Storage ────────────────────────────────────
    azure_storage_account_name: str = ""
    azure_storage_container_name: str = "documents"
    azure_storage_connection_string: str = ""  # Optional: leave blank for keyless

    # ── Azure Content Understanding ───────────────────────────
    azure_cu_endpoint: str = ""
    azure_cu_analyzer_id: str = "doc-review-analyzer"
    azure_cu_api_key: str = ""              # Optional: leave blank for keyless

    # ── App ───────────────────────────────────────────────────
    app_name: str = "Doc-Review PoC"
    app_version: str = "0.1.0"
    debug: bool = True

    @property
    def use_api_keys(self) -> bool:
        """True if at least one API key is configured (partial key fallback mode)."""
        return bool(
            self.azure_openai_api_key
            or self.azure_search_api_key
            or self.azure_cu_api_key
            or self.azure_storage_connection_string
        )

    @property
    def blob_account_url(self) -> str:
        return f"https://{self.azure_storage_account_name}.blob.core.windows.net"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — import and call this everywhere."""
    return Settings()
