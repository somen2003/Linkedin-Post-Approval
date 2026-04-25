import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app import models  # noqa: F401 — register models
from app.routers import pages, posts, approvals

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Auto-create tables on startup (idempotent).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LinkedIn Post Approval Workflow", version="1.0.0")

_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

app.include_router(pages.router)
app.include_router(posts.router)
app.include_router(approvals.router)


@app.get("/healthz")
def health():
    return {"status": "ok"}
