"""
AutoAudit AI — FastAPI application entry point (v2 — LangGraph edition).

What's new vs v1:
  · LangGraph multi-agent pipeline replaces the linear pipeline
  · WebSocket endpoint for real-time agent log streaming
  · Duplicate detection via ChromaDB (initialised on startup)
  · Audit trail service (in-memory, queryable via /demo/audit-trail)
  · Demo endpoints for failure scenario simulation (/demo/*)
  · Tenacity retry on all LLM calls (3× with exp. back-off)
"""
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings
from routes.demo import router as demo_router
from routes.upload import router as upload_router
from routes.websocket_route import router as ws_router

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Lifespan: startup / shutdown hooks ──────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    if not settings.groq_api_key:
        logger.warning(
            "GROQ_API_KEY is not set — LLM calls will fail. "
            "Create a .env file in the backend/ directory."
        )

    # Initialise ChromaDB duplicate detector (lazy model load)
    from services.duplicate_detector import duplicate_detector
    duplicate_detector.initialise()

    # Import and log the compiled graph (validates nodes + edges at startup)
    from graph.workflow import audit_workflow  # noqa: F401
    logger.info("LangGraph audit workflow ready.")

    logger.info("%s is ready to receive requests.", settings.app_name)
    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down %s.", settings.app_name)


# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AutoAudit AI is an autonomous, multi-agent invoice compliance system "
        "powered by LangGraph + Groq LLaMA 3. Upload a PDF invoice to run the "
        "full audit pipeline: extraction → duplicate check → compliance scan → "
        "LLM investigation → auto-remediation → audit report."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────

app.include_router(upload_router)   # POST /upload
app.include_router(ws_router)       # WS   /ws
app.include_router(demo_router)     # POST /demo/* | GET /demo/*


# ─── System endpoints ─────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="Health check")
async def health_check() -> JSONResponse:
    from services.duplicate_detector import duplicate_detector
    from services.websocket_manager import ws_manager

    return JSONResponse(
        content={
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
            "websocket_connections": ws_manager.connection_count,
            "duplicate_store_size": duplicate_detector.stored_count,
        }
    )


@app.get("/", tags=["System"], summary="Root")
async def root() -> JSONResponse:
    return JSONResponse(
        content={
            "app": settings.app_name,
            "version": settings.app_version,
            "endpoints": {
                "upload":               "POST /upload",
                "websocket":            "WS   /ws",
                "demo_ocr_failure":     "POST /demo/ocr-failure",
                "demo_api_timeout":     "POST /demo/api-timeout",
                "demo_bad_fix":         "POST /demo/bad-fix",
                "audit_trail_list":     "GET  /demo/audit-trail",
                "audit_trail_detail":   "GET  /demo/audit-trail/{invoice_number}",
                "system_stats":         "GET  /demo/stats",
                "docs":                 "GET  /docs",
                "health":               "GET  /health",
            },
        }
    )


# ─── Dev runner ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
