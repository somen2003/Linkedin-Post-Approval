import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app import models  # noqa: F401 — register models
from app.routers import pages, posts, approvals

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="LinkedIn Post Approval Workflow", version="1.0.0")

_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

app.include_router(pages.router)
app.include_router(posts.router)
app.include_router(approvals.router)


@app.on_event("startup")
def init_db() -> None:
    """Create tables on first request. Wrapped so import-time DB errors don't crash the function."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured.")
    except Exception:
        logger.exception("Failed to initialize database tables. Check DATABASE_URL.")


@app.get("/healthz")
def health():
    return {"status": "ok"}
