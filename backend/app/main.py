from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routes.evaluate import router as evaluate_router

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")
load_dotenv()

app = FastAPI(title="Profile Evaluation Agent")
app.include_router(evaluate_router, prefix="/api", tags=["evaluation"])

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/status")
def status():
    return {
        "ok": True,
        "service": "careerlens",
        "llm_enabled": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})
