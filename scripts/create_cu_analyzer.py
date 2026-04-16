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
import time
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import get_settings
from backend.core.auth import get_credential, get_cu_api_key


CU_API_VERSION = "2025-11-01"


# ── Analyzer schema ────────────────────────────────────────────
# Customise these fields for your customer's specific document type.
# For the workshop, this covers common doc-review scenarios.

def build_analyzer_schema(settings) -> dict:
    return {
        "description": "General document review analyzer for contracts, invoices, and business documents",
        "baseAnalyzerId": "prebuilt-document",
        "models": {
            "completion": settings.azure_cu_llm_model,
            "embedding": settings.azure_cu_embedding_model,
        },
        "config": {
            "returnDetails": True,
            "enableOcr": True,
            "enableLayout": True,
            "enableFormula": True,
            "estimateFieldSourceAndConfidence": True,
            "enableSegment": False,
            "omitContent": False,
            "segmentPerPage": False,
            "annotationFormat": "markdown"
        },
        "fieldSchema": {
            "name": "DocReviewAnalysis",
            "fields": {
                "DocumentTitle": {
                    "type": "string",
                    "method": "generate",
                    "description": "The title or name of the document"
                },
                "DocumentDate": {
                    "type": "date",
                    "method": "generate",
                    "description": "The date the document was created or signed"
                },
                "EffectiveDate": {
                    "type": "date",
                    "method": "generate",
                    "description": "The date the document becomes effective"
                },
                "ExpirationDate": {
                    "type": "date",
                    "method": "generate",
                    "description": "The expiration or end date of the agreement"
                },
                "PartyA": {
                    "type": "string",
                    "method": "generate",
                    "description": "The first party or company named in the document"
                },
                "PartyB": {
                    "type": "string",
                    "method": "generate",
                    "description": "The second party or company named in the document"
                },
                "TotalAmount": {
                    "type": "number",
                    "method": "generate",
                    "description": "The total monetary value or contract amount"
                },
                "Currency": {
                    "type": "string",
                    "method": "generate",
                    "description": "The currency of any monetary amounts"
                },
                "GoverningLaw": {
                    "type": "string",
                    "method": "generate",
                    "description": "The governing law or jurisdiction"
                },
                "DocumentType": {
                    "type": "string",
                    "method": "generate",
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


def ensure_defaults(client: httpx.Client, base_endpoint: str, headers: dict, settings) -> None:
    desired_mappings = {}
    if settings.azure_cu_llm_deployment:
        desired_mappings["gpt-4.1"] = settings.azure_cu_llm_deployment
    if settings.azure_cu_embedding_deployment:
        desired_mappings["text-embedding-3-large"] = settings.azure_cu_embedding_deployment

    if not desired_mappings:
        print("⚠️  Skipping CU defaults configuration because deployment names are not set.")
        print("   Set AZURE_CU_LLM_DEPLOYMENT and AZURE_CU_EMBEDDING_DEPLOYMENT in .env.")
        return

    defaults_url = (
        f"{base_endpoint}/contentunderstanding/defaults"
        f"?api-version={CU_API_VERSION}"
    )

    existing_mappings = {}
    resp = client.get(defaults_url, headers=headers)
    if resp.status_code == 200:
        existing_mappings = resp.json().get("modelDeployments", {})
    elif resp.status_code == 400 and "DefaultsNotSet" in resp.text:
        existing_mappings = {}
    else:
        resp.raise_for_status()

    if all(existing_mappings.get(key) == value for key, value in desired_mappings.items()):
        print("✅ Content Understanding defaults already configured.")
        return

    merged_mappings = {**existing_mappings, **desired_mappings}
    print("⏳ Configuring Content Understanding model defaults...")
    resp = client.patch(
        defaults_url,
        headers=headers,
        json={"modelDeployments": merged_mappings},
    )
    resp.raise_for_status()
    print("✅ Content Understanding defaults configured.")


def wait_for_analyzer_ready(
    client: httpx.Client,
    analyzer_url: str,
    headers: dict,
    max_wait_seconds: int = 180,
    poll_interval: float = 5.0,
) -> dict:
    deadline = time.time() + max_wait_seconds
    last_body = None

    while time.time() < deadline:
        resp = client.get(analyzer_url, headers=headers)
        resp.raise_for_status()
        last_body = resp.json()
        status = last_body.get("status", "").lower()

        if status == "ready":
            return last_body
        if status == "failed":
            raise RuntimeError(f"Analyzer creation failed: {json.dumps(last_body, indent=2)}")

        time.sleep(poll_interval)

    raise TimeoutError(
        f"Analyzer did not become ready within {max_wait_seconds}s. Last status: {json.dumps(last_body, indent=2)}"
    )


def main():
    settings = get_settings()
    base_endpoint = settings.azure_cu_endpoint.rstrip("/")

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
    analyzer_schema = build_analyzer_schema(settings)

    with httpx.Client(timeout=30) as client:
        ensure_defaults(client, base_endpoint, headers, settings)

        analyzer_url = (
            f"{base_endpoint}/contentunderstanding/analyzers"
            f"/{settings.azure_cu_analyzer_id}"
            f"?api-version={CU_API_VERSION}"
        )

        existing_status = ""
        resp = client.get(analyzer_url, headers=headers)
        if resp.status_code == 200:
            existing_status = resp.json().get("status", "")
            if existing_status.lower() == "ready":
                print(f"✅ Analyzer '{settings.azure_cu_analyzer_id}' already exists and is ready.")
                return
            print(f"⏳ Analyzer '{settings.azure_cu_analyzer_id}' exists with status '{existing_status}'. Replacing it...")
        elif resp.status_code in (401, 403):
            print("❌ Authentication failed. Make sure you're logged in: az login")
            print(f"   Response: {resp.text}")
            sys.exit(1)
        elif resp.status_code != 404:
            resp.raise_for_status()

        # ── Create analyzer ────────────────────────────────────
        create_url = f"{analyzer_url}&allowReplace=true"

        print(f"⏳ Creating analyzer '{settings.azure_cu_analyzer_id}'...")
        print(f"   Fields: {', '.join(analyzer_schema['fieldSchema']['fields'].keys())}")
        print()

        resp = client.put(create_url, headers=headers, json=analyzer_schema)

        if resp.status_code in (200, 201):
            analyzer = wait_for_analyzer_ready(client, analyzer_url, headers)
            print(f"✅ Analyzer '{settings.azure_cu_analyzer_id}' created successfully!")
            print(f"   Status: {analyzer.get('status')}")
        else:
            print(f"❌ Failed to create analyzer: {resp.status_code}")
            print(f"   {resp.text}")
            print()
            print("💡 You can also create the analyzer manually:")
            print("   1. Go to https://ai.azure.com")
            print("   2. Navigate to your project → Content Understanding")
            print("   3. Create a new analyzer with the schema below:")
            print()
            print(json.dumps(analyzer_schema, indent=2))
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
