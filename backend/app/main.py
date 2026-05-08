from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")
load_dotenv()

from app.routes.evaluate import router as evaluate_router

app = FastAPI(
    title="Profile Evaluation Agent",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(evaluate_router, prefix="/api", tags=["evaluation"])

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/status")
def status():
    return {
        "ok": True,
        "service": "careerlens",
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
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0").strip() or "0.0.0.0"
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("RELOAD", "false").strip().lower() in {"1", "true", "yes"}
    uvicorn.run("app.main:app", host=host, port=port, reload=reload_enabled)
