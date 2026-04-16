"""
backend/main.py
───────────────
FastAPI application entry point.

Run with:
    uvicorn backend.main:app --reload --port 8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

from backend.core.config import get_settings
from backend.routers import upload, analyze, search, chat

# ── App init ──────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Doc-Review PoC powered by Azure AI Foundry",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────

app.include_router(upload.router,  prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(search.router,  prefix="/api")
app.include_router(chat.router,    prefix="/api")

# ── Static files & templates ──────────────────────────────────

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))


# ── Routes ────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "app_name": settings.app_name},
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "auth_mode": "api_key_fallback" if settings.use_api_keys else "keyless (DefaultAzureCredential)",
    }


# ── Package init files ────────────────────────────────────────

# (Listed here as a reminder — created as empty files in their directories)
