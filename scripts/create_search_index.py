#!/usr/bin/env python3
"""
scripts/create_search_index.py
───────────────────────────────
One-time setup: creates the Azure AI Search index for doc-review.

Run once before starting the app:
    python scripts/create_search_index.py

Uses DefaultAzureCredential (az login) by default.
Set AZURE_SEARCH_API_KEY in .env for API key mode.
"""

import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import get_settings
from backend.services.search_service import create_index_if_not_exists, get_index_client


def main():
    settings = get_settings()

    print("=" * 60)
    print("  Doc-Review PoC — Search Index Setup")
    print("=" * 60)
    print(f"\n  Endpoint  : {settings.azure_search_endpoint}")
    print(f"  Index     : {settings.azure_search_index_name}")
    print(f"  Auth mode : {'API Key' if settings.azure_search_api_key else 'DefaultAzureCredential (keyless)'}")
    print()

    if not settings.azure_search_endpoint:
        print("❌ AZURE_SEARCH_ENDPOINT is not set in .env")
        print("   Please configure your Azure AI Search endpoint and try again.")
        sys.exit(1)

    # Check if index already exists
    index_client = get_index_client()
    existing = [idx.name for idx in index_client.list_index_names()]

    if settings.azure_search_index_name in existing:
        print(f"✅ Index '{settings.azure_search_index_name}' already exists. Nothing to do.")
        print("\n   To recreate it, delete it first in Azure Portal → AI Search → Indexes")
        return

    print(f"⏳ Creating index '{settings.azure_search_index_name}'...")
    created = create_index_if_not_exists()

    if created:
        print(f"\n✅ Index '{settings.azure_search_index_name}' created successfully!")
        print("""
   The index includes:
     • id          — unique chunk identifier
     • doc_id      — document identifier (filterable)
     • filename    — original filename (filterable)
     • chunk       — text content (searchable, en.microsoft analyzer)
     • chunk_index — position within document

   Semantic configuration 'default' is enabled for best relevance.

   Next step: Run the app and upload a document!
        """)
    else:
        print("⚠️  Index already existed (race condition). You're good to go.")


if __name__ == "__main__":
    main()
