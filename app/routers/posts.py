import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_employee_by_name, get_approver_for_level
from app.database import get_db
from app.models import Post
from app.services import workflow, email_service

logger = logging.getLogger(__name__)
router = APIRouter()

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.post("/api/posts", response_class=HTMLResponse)
def submit_post(
    request: Request,
    submitter_name: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    employee = get_employee_by_name(submitter_name)
    if not employee:
        raise HTTPException(status_code=400, detail="Unknown submitter. Pick a name from the dropdown.")

    content = content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content is required.")

    chain = workflow.build_chain(employee.role)
    if not chain:
        raise HTTPException(status_code=400, detail="No approvers in the workflow chain.")

    post = Post(
        content=content,
        submitter_name=employee.name,
        submitter_email=employee.email,
        submitter_role=employee.role,
        approval_chain=chain,
        current_step=0,
        status="PENDING",
    )
    db.add(post)
    db.flush()

    first_level = chain[0]
    approver = get_approver_for_level(first_level)
    if not approver:
        raise HTTPException(
            status_code=500,
            detail=f"No approver configured for level {first_level}. Edit EMPLOYEES in app/config.py.",
        )

    approve_token = workflow.create_action_token(db, post, first_level, approver.email)
    reject_token = workflow.create_action_token(db, post, first_level, approver.email)
    db.commit()

    email_ok = True
    try:
        email_service.send_approval_request(
            to_email=approver.email,
            approver_name=approver.name,
            level=first_level,
            post_content=content,
            submitter_name=employee.name,
            submitter_email=employee.email,
            submitter_role=employee.role,
            approve_token=approve_token,
            reject_token=reject_token,
        )
    except Exception:
        logger.exception("Failed to send approval email for post %s", post.id)
        email_ok = False

    return templates.TemplateResponse(
        "submitted.html",
        {"request": request, "ok": email_ok},
    )