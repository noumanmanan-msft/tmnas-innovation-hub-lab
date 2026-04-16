# 🎓 Workshop Facilitator Guide
## Doc-Review PoC — Azure AI Foundry

**Audience:** Customer technical team + business stakeholders  
**Duration:** 45–90 minutes (scale to available time)  
**Goal:** Live PoC demonstrating AI-powered document review using their own Azure resources

---

## 🗂️ Pre-Workshop Checklist (Do Before You Arrive)

- [ ] Customer has an **Azure AI Foundry project** created at https://ai.azure.com
- [ ] Customer has **GPT-4o** deployed in Azure OpenAI
- [ ] Customer has **Azure AI Search** resource (Basic tier or above for semantic search)
- [ ] Customer has **Azure Blob Storage** account
- [ ] Customer has provisioned **Azure Content Understanding** (part of AI Foundry)
- [ ] You have `az login` working on your laptop with access to their subscription
- [ ] `pip install -r requirements.txt` completed
- [ ] `.env` file populated with customer's resource values

> 💡 **If resources aren't ready:** The chat and analyze-text endpoints can run with just Azure OpenAI. You can demo GPT-4o analysis without Blob/Search/CU.

---

## ⚙️ Setup Steps (Run at Customer Site)

### Step 1 — Configure environment

```bash
cp .env.example .env
# Open .env and fill in customer's Azure resource endpoints
```

Get values from: **Azure Portal → AI Foundry → your project → Overview**

### Step 2 — Authenticate

```bash
az login
az account set --subscription "<customer-subscription-id>"
```

Verify: `az account show` — confirms logged in identity

### Step 3 — Provision the search index

```bash
python scripts/create_search_index.py
```

Expected output: `✅ Index 'doc-review-index' created successfully!`

### Step 4 — Provision the Content Understanding analyzer

```bash
python scripts/create_cu_analyzer.py
```

Expected output: `✅ Analyzer 'docreviewanalyzer' created successfully!`

> ⚠️ If CU is not available, skip this step. The /analyze endpoint will fail gracefully; you can still demo /chat with raw text.

### Step 5 — Start the application

```bash
uvicorn backend.main:app --reload --port 8000
```

Open **http://localhost:8000** — you should see the Doc-Review UI.

---

## 🎬 Demo Script

### Act 1 — Upload (5 min)

**Say:** *"Let's start by uploading a document. We have a sample Master Services Agreement — a common document that legal and procurement teams review every day."*

1. Click the **Upload** tab
2. Drag `sample_docs/sample_contract.txt` onto the drop zone (or click Browse)
3. Click **Upload to Azure Blob Storage**
4. Show the result: `doc_id`, `blob_url`, `size_bytes`

**Key point:** *"The document is now stored securely in your Azure Blob Storage. Notice there are no API keys — we're using your Azure identity, the same one your team uses for everything else."*

---

### Act 2 — Extract (10 min)

**Say:** *"Now let's run Content Understanding. This isn't just OCR — it's a layout-aware AI that understands the structure of your specific document type."*

1. Click the **Analyze** tab
2. The `doc_id` should be pre-filled (if not, paste it)
3. Click **Run Extraction + Index**
4. Walk through the extracted fields:
   - `DocumentTitle`, `PartyA`, `PartyB`
   - `EffectiveDate`, `ExpirationDate`
   - `TotalAmount`, `GoverningLaw`
5. Point out the **confidence scores** per field
6. Show the **raw extracted text** — mention it's been indexed into AI Search

**Key point:** *"These fields are customisable. For your invoice process you'd extract vendor name, PO number, line items. For compliance docs, you'd extract jurisdiction, regulation references. The analyzer schema lives in `scripts/create_cu_analyzer.py`."*

---

### Act 3 — GPT-4o Analysis (5 min)

**Say:** *"Now let's have GPT-4o do a full legal review."*

1. Still on Analyze tab, click **Analyze with GPT-4o**
2. Walk through the structured output:
   - Summary
   - Key Parties
   - Critical Dates
   - Key Obligations
   - **Risks / Red Flags** ← this usually gets the most reaction
   - Recommended Actions

**Key point:** *"This is GPT-4o grounded in the actual document content — not hallucinating. Notice it found the liability cap clause and the auto-renewal clause. Those are exactly the things your reviewers spend hours looking for."*

---

### Act 4 — Semantic Search (5 min)

**Say:** *"Now let's show how your team can search across hundreds of documents — not keyword search, but meaning-based search."*

1. Click the **Search** tab
2. Try these queries one by one:
   - `"What are the payment terms?"` → should return Section 2 chunks
   - `"termination notice period"` → should return Section 3
   - `"liability cap amount"` → should return Section 7

3. Toggle **Use Semantic Ranker** off and on — show score differences

**Key point:** *"This is Azure AI Search's semantic ranker — it understands meaning, not just keywords. 'Termination notice period' finds Section 3.3 even though those exact words don't appear together."*

---

### Act 5 — Chat (10–15 min)

**Say:** *"This is where it all comes together — a conversational interface grounded in your documents."*

1. Click the **Chat** tab
2. Use quick prompt buttons on the left:
   - **Summarize** → show the overview
   - **Key obligations** → show what each party must do
   - **Risks & red flags** → this is always a highlight
3. Ask a custom question:
   - *"What happens if Fabrikam doesn't pay on time?"*
   - *"Can Contoso use subcontractors?"*
   - *"When does this contract expire and how do I renew it?"*
4. Show the **Sources** panel at the bottom — point out the exact chunks retrieved

5. Ask a question the document *doesn't* answer:
   - *"What is the SLA for bug fixes?"*
   → GPT-4o should say it's not in the document

**Key point:** *"See how it says 'not in the document' rather than making something up. That's the grounding — it only answers from what's actually there."*

---

### Act 6 — Architecture Discussion (10 min)

Draw or point to the architecture in README.md:

```
Frontend → FastAPI → [Blob Storage | Content Understanding | AI Search | GPT-4o]
```

**Discussion points:**

- **DefaultAzureCredential** → "No keys, no secrets management — same identity as your CI/CD"
- **RAG pattern** → "Why does this matter vs. just sending the whole doc to GPT-4o? Cost, context limits, multi-doc scenarios"
- **Content Understanding vs. Document Intelligence** → "CU is schema-first, model-aware, built for Foundry"
- **Extensibility** → "Swap in your real documents, tune the CU analyzer, add Azure AI Evaluation for quality scoring"

---

## 🔧 Troubleshooting

| Issue | Fix |
|---|---|
| `az login` not working | Use `az login --use-device-code` |
| Content Understanding returns 404 | CU endpoint must be the AI Foundry project endpoint, not AI Services endpoint |
| Search returns 0 results | Run analyze first to index the document |
| GPT-4o returns auth error | Verify `AZURE_OPENAI_ENDPOINT` matches the deployment region |
| Blob upload fails | Check `AZURE_STORAGE_ACCOUNT_NAME` and that your identity has `Storage Blob Data Contributor` role |
| Semantic search fails | Basic tier required; toggle semantic off to demo keyword search |

---

## 💡 Talking Points by Audience

### For IT / Architects
- DefaultAzureCredential → no secrets, RBAC-controlled, enterprise-ready
- Containerise with Docker, deploy to Azure Container Apps
- Swap AI Search for a vector DB (pgvector, Redis, Qdrant) if preferred
- Extend with Azure AI Evaluation for quality gates

### For Business / Legal Stakeholders
- Hours of review → seconds of extraction
- Consistency: same fields extracted the same way, every time
- Audit trail: every extraction stored in Azure
- Not replacing reviewers — giving them superpowers

### For Procurement / Finance
- Runs entirely on your Azure tenant — data never leaves your environment
- Pay-as-you-go: only charged for what you use
- Existing Azure credits apply

---

## 🚀 Next Steps to Suggest

1. **Tune the CU analyzer** for customer's specific document type (add their fields)
2. **Connect to their real document repository** (SharePoint, OneDrive, S3)
3. **Add Azure AI Evaluation** to score extraction accuracy
4. **Build a Power App** on top of this API for non-technical users
5. **Add multi-doc comparison** for contract redlining
6. **Production hardening**: auth, rate limiting, logging, Azure Monitor
