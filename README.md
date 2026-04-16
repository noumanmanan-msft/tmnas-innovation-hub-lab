# 📄 Doc-Review PoC — Azure AI Foundry Workshop

A hands-on boilerplate for building an intelligent document review application using **Azure AI Foundry**, **Azure OpenAI (GPT-4o)**, **Azure AI Search**, **Azure Blob Storage**, and **Azure Content Understanding**.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (HTML/Tailwind)              │
│         Upload Docs │ Ask Questions │ View Analysis          │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼────────────────────────────────┐
│                    FastAPI Backend                           │
│   /upload  │  /analyze  │  /search  │  /chat                │
└────┬───────┴──────┬──────┴─────┬────┴────────┬─────────────┘
     │              │             │              │
 Blob Storage  Content       AI Search       Azure OpenAI
 (doc store)  Understanding   (RAG index)    GPT-4o (chat)
              (extraction)
```

---

## 🧰 Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | `python --version` |
| Azure CLI | `az --version` |
| Azure Subscription | With AI Foundry / AI Services access |
| Azure AI Foundry Project | Create at https://ai.azure.com |

---

## ⚡ Quick Start

### 1. Clone & Install

```bash
git clone <your-repo>
cd doc-review-poc

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Authenticate with Azure (Keyless — Recommended)

```bash
az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
```

> **No API keys needed.** This boilerplate uses `DefaultAzureCredential` which automatically picks up your `az login` session, managed identity in production, or environment variables as a fallback.

### 3. Configure Your Resources

Copy the example config and fill in your Azure resource details:

```bash
cp .env.example .env
```

Edit `.env` with your values (see [Configuration Reference](#-configuration-reference) below).

### 4. Run the App

```bash
uvicorn backend.main:app --reload --port 8000
```

Visit **http://localhost:8000** in your browser.

---

## 🤖 Automated Azure Provisioning (No Portal Required)

If you want customers to create all required lab resources from CLI only, use the new numbered scripts.

### What these scripts do

1. Log in to Azure via `az` CLI.
2. Select the subscription (optional, if provided).
3. Create the resource group if it does not exist.
4. Create required resources for this lab:
    - Azure Storage account + `documents` blob container
    - Azure AI Search service
    - Azure OpenAI account + model deployment
    - Azure AI Services account for Content Understanding endpoint/key
5. Generate a ready-to-run `.env` file from created resources.
6. Optionally run bootstrap scripts to create the Search index and Content Understanding analyzer.

### Bash (Linux/macOS)

Update variables first:

- `scripts/bash/00-variables.sh`

Run in order:

```bash
bash scripts/bash/01-login.sh
bash scripts/bash/02-create-resource-group.sh
bash scripts/bash/03-create-resources.sh
bash scripts/bash/04-generate-env-and-bootstrap.sh
```

### PowerShell (Windows / PowerShell Core)

Update variables first:

- `scripts/powershell/00-variables.ps1`

Run in order:

```powershell
pwsh ./scripts/powershell/01-login.ps1
pwsh ./scripts/powershell/02-create-resource-group.ps1
pwsh ./scripts/powershell/03-create-resources.ps1
pwsh ./scripts/powershell/04-generate-env-and-bootstrap.ps1
```

> Notes:
> - Keep the same suffix/name values across all steps.
> - OpenAI deployment can fail if model quota or region availability is insufficient; adjust model/region in the `00-variables` file and rerun step 03.
> - After provisioning finishes, run the app with `uvicorn backend.main:app --reload --port 8000`.

---

## 🔧 Configuration Reference

Edit `.env` with the values from your Azure AI Foundry project:

```
# ── Azure AI Foundry Project ──────────────────────────────────
AZURE_SUBSCRIPTION_ID=         # Your subscription ID
AZURE_RESOURCE_GROUP=          # Resource group name
AZURE_AI_PROJECT_NAME=         # AI Foundry project name
AZURE_AI_PROJECT_ENDPOINT=     # e.g. https://<name>.services.ai.azure.com

# ── Azure OpenAI ──────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT=         # e.g. https://<name>.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=       # e.g. gpt-4o
AZURE_OPENAI_API_VERSION=      # e.g. 2024-12-01-preview

# ── Azure AI Search ───────────────────────────────────────────
AZURE_SEARCH_ENDPOINT=         # e.g. https://<name>.search.windows.net
AZURE_SEARCH_INDEX_NAME=       # e.g. doc-review-index

# ── Azure Blob Storage ────────────────────────────────────────
AZURE_STORAGE_ACCOUNT_NAME=    # e.g. mystorageaccount
AZURE_STORAGE_CONTAINER_NAME=  # e.g. documents

# ── Azure Content Understanding ───────────────────────────────
AZURE_CU_ENDPOINT=             # e.g. https://<name>.cognitiveservices.azure.com
AZURE_CU_ANALYZER_ID=          # e.g. doc-review-analyzer (create in AI Foundry)

# ── Optional: API Key Fallback ────────────────────────────────
# Only set these if DefaultAzureCredential does not work in your environment.
# Leave blank to use keyless auth (recommended).
# AZURE_OPENAI_API_KEY=
# AZURE_SEARCH_API_KEY=
# AZURE_CU_API_KEY=
```

> 💡 **Finding your values:** In [Azure AI Foundry](https://ai.azure.com) → your project → **Overview** tab → Connection details

---

## 📁 Project Structure

```
doc-review-poc/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── core/
│   │   ├── config.py            # Settings / env loading
│   │   └── auth.py              # DefaultAzureCredential setup
│   ├── services/
│   │   ├── blob_service.py      # Upload/download docs from Blob Storage
│   │   ├── content_understanding.py  # Azure Content Understanding extraction
│   │   ├── search_service.py    # Index + query Azure AI Search
│   │   └── openai_service.py    # GPT-4o chat + analysis
│   ├── routers/
│   │   ├── upload.py            # POST /upload
│   │   ├── analyze.py           # POST /analyze
│   │   ├── search.py            # GET  /search
│   │   └── chat.py              # POST /chat
│   └── models/
│       └── schemas.py           # Pydantic request/response models
├── frontend/
│   ├── templates/
│   │   └── index.html           # Main UI (Tailwind CSS)
│   └── static/
│       ├── css/custom.css
│       └── js/app.js
├── scripts/
│   ├── create_search_index.py   # One-time: provision AI Search index
│   └── create_cu_analyzer.py    # One-time: provision Content Understanding analyzer
├── sample_docs/
│   └── sample_contract.txt      # Demo document for the workshop
├── docs/
│   └── WORKSHOP_GUIDE.md        # Step-by-step facilitator guide
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🎓 Workshop Flow (30–60 min)

| Step | Action | File |
|---|---|---|
| 1 | Set up `.env` with customer's Foundry resources | `.env` |
| 2 | Run `create_search_index.py` | `scripts/` |
| 3 | Run `create_cu_analyzer.py` | `scripts/` |
| 4 | Start the app, upload `sample_contract.txt` | UI |
| 5 | Walk through Content Understanding extraction | UI → `/analyze` |
| 6 | Ask questions via the chat interface | UI → `/chat` |
| 7 | Show indexed chunks in AI Search | UI → `/search` |

See **[docs/WORKSHOP_GUIDE.md](docs/WORKSHOP_GUIDE.md)** for the full facilitator script.

---

## 🔑 Authentication Deep Dive

This project uses **`DefaultAzureCredential`** — no hardcoded keys required.

It attempts credentials in this order:
1. `EnvironmentCredential` — env vars like `AZURE_CLIENT_ID` (CI/CD)
2. `WorkloadIdentityCredential` — AKS workload identity
3. `ManagedIdentityCredential` — Azure-hosted compute (App Service, etc.)
4. **`AzureCliCredential`** — your local `az login` ✅ *(workshop default)*
5. `VisualStudioCodeCredential` — VS Code Azure extension

> If API keys are needed as a fallback, set `AZURE_OPENAI_API_KEY` etc. in `.env` — the code will detect and use them automatically.

---

## 🚀 Extending This PoC

Ideas to take it further:
- Add **multi-doc comparison** (upload 2 contracts, diff clauses)
- Integrate **Azure AI Evaluation** to score extraction quality
- Add **citation grounding** with Search semantic ranker
- Deploy to **Azure Container Apps** with managed identity
- Connect to **Microsoft Fabric** for doc analytics at scale
