from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")
load_dotenv()

from app.routes.analyze import router as analyze_router
from app.routes.evaluate import router as evaluate_router
from app.routes.auth import router as auth_router
from app.routes.profile import router as profile_router
from app.auth.deps import auth_required
from app.db.database import USE_POSTGRES, init_db

app = FastAPI(
    title="Profile Evaluation Agent",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(analyze_router, prefix="/api", tags=["analyze"])
app.include_router(evaluate_router, prefix="/api", tags=["evaluation"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(profile_router, prefix="/api", tags=["profile"])

cors_origins_raw = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
)
cors_origins = [x.strip() for x in cors_origins_raw.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _route_registered(method: str, path: str) -> bool:
    """True if this process actually registered the route (detects stale servers on :8000)."""
    for r in app.routes:
        if getattr(r, "path", None) != path:
            continue
        methods = getattr(r, "methods", None) or set()
        if method in methods:
            return True
    return False


@app.get("/status")
def status():
    return {
        "ok": True,
        "service": "careerlens",
        "database": "postgresql" if USE_POSTGRES else "sqlite",
        "auth_required": auth_required(),
        "cors_origins": cors_origins,
        "llm_enabled": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "linkedin_automation": {
            "apify_configured": bool(os.getenv("APIFY_API_TOKEN", "").strip()),
            "apify_actor": os.getenv(
                "APIFY_LINKEDIN_ACTOR_ID", "harvestapi/linkedin-profile-scraper"
            ),
            "phantombuster_configured": bool(
                os.getenv("PHANTOMBUSTER_API_KEY", "").strip()
                and os.getenv("PHANTOMBUSTER_AGENT_ID", "").strip()
            ),
        },
        "google_oauth_configured": bool(os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()),
        "post_auth_google_registered": _route_registered("POST", "/api/auth/google"),
    }

@app.get("/")
def root():
    return {
        "ok": True,
        "service": "careerlens-api",
        "message": "API server is running. Use /api/evaluate and /status.",
    }


@app.on_event("startup")
def _startup():
    try:
        init_db()
    except Exception as e:
        import sys

        err = f"{type(e).__name__}: {e}"
        low = err.lower()
        if any(
            x in low
            for x in (
                "postgresql",
                "postgres",
                "5432",
                "connection refused",
                "operationalerror",
                "psycopg2",
                "could not connect",
            )
        ):
            print(
                "\n>>> CareerLens: database startup failed.\n"
                "    If you are NOT running PostgreSQL locally, comment out DATABASE_URL in backend/.env\n"
                "    so the app uses SQLite (default: backend/careerlens.db). See backend/.env.example.\n"
                f">>> ({err})\n",
                file=sys.stderr,
                flush=True,
            )
        raise


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0").strip() or "0.0.0.0"
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("RELOAD", "false").strip().lower() in {"1", "true", "yes"}
    uvicorn.run("app.main:app", host=host, port=port, reload=reload_enabled)
