#!/usr/bin/env python3
"""
scripts/create_cu_analyzer.py
──────────────────────────────
One-time setup: creates a Content Understanding analyzer in Azure AI Foundry
for the doc-review use-case.

Run once before starting the app:
    python scripts/create_cu_analyzer.py

The analyzer is configured for general document review — it extracts
common fields found in contracts, invoices, and business documents.
Customise the `field_schema` below for your specific use-case.

Uses DefaultAzureCredential (az login) by default.
Set AZURE_CU_API_KEY in .env for API key mode.

Docs: https://learn.microsoft.com/azure/ai-services/content-understanding/
"""

import sys
import json
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import get_settings
from backend.core.auth import get_credential, get_cu_api_key


# ── Analyzer schema ────────────────────────────────────────────
# Customise these fields for your customer's specific document type.
# For the workshop, this covers common doc-review scenarios.

ANALYZER_SCHEMA = {
    "description": "General document review analyzer for contracts, invoices, and business documents",
    "scenario": "documentIntelligence",
    "fieldSchema": {
        "fields": {
            "DocumentTitle": {
                "type": "string",
                "description": "The title or name of the document"
            },
            "DocumentDate": {
                "type": "date",
                "description": "The date the document was created or signed"
            },
            "EffectiveDate": {
                "type": "date",
                "description": "The date the document becomes effective"
            },
            "ExpirationDate": {
                "type": "date",
                "description": "The expiration or end date of the agreement"
            },
            "PartyA": {
                "type": "string",
                "description": "The first party or company named in the document"
            },
            "PartyB": {
                "type": "string",
                "description": "The second party or company named in the document"
            },
            "TotalAmount": {
                "type": "number",
                "description": "The total monetary value or contract amount"
            },
            "Currency": {
                "type": "string",
                "description": "The currency of any monetary amounts"
            },
            "GoverningLaw": {
                "type": "string",
                "description": "The governing law or jurisdiction"
            },
            "DocumentType": {
                "type": "string",
                "description": "The type of document (e.g. NDA, MSA, SOW, Invoice)"
            }
        }
    }
}


def get_headers() -> dict:
    api_key = get_cu_api_key()
    if api_key:
        return {
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/json",
        }
    credential = get_credential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    return {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }


def main():
    settings = get_settings()

    print("=" * 60)
    print("  Doc-Review PoC — Content Understanding Analyzer Setup")
    print("=" * 60)
    print(f"\n  Endpoint    : {settings.azure_cu_endpoint}")
    print(f"  Analyzer ID : {settings.azure_cu_analyzer_id}")
    print(f"  Auth mode   : {'API Key' if settings.azure_cu_api_key else 'DefaultAzureCredential (keyless)'}")
    print()

    if not settings.azure_cu_endpoint:
        print("❌ AZURE_CU_ENDPOINT is not set in .env")
        print("   This should be your Azure AI Foundry project endpoint.")
        sys.exit(1)

    headers = get_headers()

    # ── Check if analyzer exists ───────────────────────────────
    list_url = (
        f"{settings.azure_cu_endpoint}/contentunderstanding/analyzers"
        f"?api-version=2024-12-01-preview"
    )

    with httpx.Client(timeout=30) as client:
        resp = client.get(list_url, headers=headers)

        if resp.status_code == 200:
            existing = [a.get("analyzerId") for a in resp.json().get("value", [])]
            if settings.azure_cu_analyzer_id in existing:
                print(f"✅ Analyzer '{settings.azure_cu_analyzer_id}' already exists. Nothing to do.")
                print("\n   To recreate it, delete it first via the Azure AI Foundry Studio.")
                return
        elif resp.status_code in (401, 403):
            print("❌ Authentication failed. Make sure you're logged in: az login")
            print(f"   Response: {resp.text}")
            sys.exit(1)

        # ── Create analyzer ────────────────────────────────────
        create_url = (
            f"{settings.azure_cu_endpoint}/contentunderstanding/analyzers"
            f"/{settings.azure_cu_analyzer_id}"
            f"?api-version=2024-12-01-preview"
        )

        print(f"⏳ Creating analyzer '{settings.azure_cu_analyzer_id}'...")
        print(f"   Fields: {', '.join(ANALYZER_SCHEMA['fieldSchema']['fields'].keys())}")
        print()

        resp = client.put(create_url, headers=headers, json=ANALYZER_SCHEMA)

        if resp.status_code in (200, 201):
            print(f"✅ Analyzer '{settings.azure_cu_analyzer_id}' created successfully!")
        elif resp.status_code == 202:
            # Async creation
            print("⏳ Analyzer creation is in progress (async)...")
            operation_url = resp.headers.get("Operation-Location")
            if operation_url:
                print(f"   Track progress: GET {operation_url}")
            print("   Wait a few minutes, then run the app.")
        else:
            print(f"❌ Failed to create analyzer: {resp.status_code}")
            print(f"   {resp.text}")
            print()
            print("💡 You can also create the analyzer manually:")
            print("   1. Go to https://ai.azure.com")
            print("   2. Navigate to your project → Content Understanding")
            print("   3. Create a new analyzer with the schema below:")
            print()
            print(json.dumps(ANALYZER_SCHEMA, indent=2))
            sys.exit(1)

    print("""
   Next steps:
     1. Run: python scripts/create_search_index.py
     2. Start the app: uvicorn backend.main:app --reload
     3. Upload a document and click 'Analyze'!

   💡 Tip: Edit ANALYZER_SCHEMA in this script to customise
      extracted fields for your customer's document type.
    """)


if __name__ == "__main__":
    main()
