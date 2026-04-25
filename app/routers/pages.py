from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.admin_auth import require_admin
from app.config import EMPLOYEES
from app.database import get_db
from app.models import Post

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def submission_form(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "employees": EMPLOYEES},
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    submitted: str = "",
    error: str = "",
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    posts = db.query(Post).order_by(Post.created_at.desc()).limit(200).all()

    flash = None
    if submitted:
        flash = "Post submitted successfully. The first approver will receive an email shortly."
    elif error == "email_failed":
        flash = "Post saved, but the approval email failed to send. Check SMTP settings."

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "posts": posts, "flash": flash},
    )
