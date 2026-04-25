import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_approver_for_level, get_all_approvers
from app.database import get_db
from app.models import Post, ApprovalToken
from app.services import workflow, email_service

logger = logging.getLogger(__name__)
router = APIRouter()

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _load_token(db: Session, raw_token: str) -> tuple[ApprovalToken, Post]:
    token, err = workflow.consume_action_token(db, raw_token)
    if err or not token:
        raise HTTPException(status_code=400, detail=err or "Invalid token.")
    post = db.query(Post).filter(Post.id == token.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    return token, post


@router.get("/approve/{raw_token}", response_class=HTMLResponse)
def approve_page(raw_token: str, request: Request, db: Session = Depends(get_db)):
    token, post = _load_token(db, raw_token)
    expected_level = workflow.current_level(post)
    if post.status != "PENDING" or token.level != expected_level:
        return templates.TemplateResponse(
            "result.html",
            {"request": request, "title": "Action not available",
             "message": f"This post is no longer awaiting {token.level} approval.",
             "post": post},
        )
    return templates.TemplateResponse(
        "confirm.html",
        {"request": request, "post": post, "token": raw_token, "action": "APPROVE", "level": token.level},
    )


@router.get("/reject/{raw_token}", response_class=HTMLResponse)
def reject_page(raw_token: str, request: Request, db: Session = Depends(get_db)):
    token, post = _load_token(db, raw_token)
    expected_level = workflow.current_level(post)
    if post.status != "PENDING" or token.level != expected_level:
        return templates.TemplateResponse(
            "result.html",
            {"request": request, "title": "Action not available",
             "message": f"This post is no longer awaiting {token.level} approval.",
             "post": post},
        )
    return templates.TemplateResponse(
        "confirm.html",
        {"request": request, "post": post, "token": raw_token, "action": "REJECT", "level": token.level},
    )


@router.post("/action/{raw_token}", response_class=HTMLResponse)
def execute_action(
    raw_token: str,
    request: Request,
    action: str = Form(...),
    comment: str = Form(default=""),
    db: Session = Depends(get_db),
):
    token, post = _load_token(db, raw_token)

    expected_level = workflow.current_level(post)
    if post.status != "PENDING" or token.level != expected_level:
        raise HTTPException(status_code=400, detail="This post is not currently awaiting this level's decision.")

    token.used_at = datetime.utcnow()
    comment = (comment or "").strip() or None

    if action.upper() == "APPROVE":
        workflow.record_approval(db, post, token.level, token.approver_email, comment)
        db.flush()

        if post.status == "APPROVED":
            approvers = get_all_approvers()
            trail = [
                {"level": log.level, "approver_email": log.approver_email, "comment": log.comment}
                for log in post.logs if log.action == "APPROVED"
            ]
            db.commit()

            for approver in approvers:
                try:
                    email_service.send_final_approved(
                        to_email=approver.email,
                        recipient_name=approver.name,
                        post_content=post.content,
                        submitter_name=post.submitter_name,
                        submitter_email=post.submitter_email,
                        approval_trail=trail,
                    )
                except Exception:
                    logger.exception("Failed sending final-approved email to %s", approver.email)

            return templates.TemplateResponse(
                "result.html",
                {"request": request, "title": "Post fully approved",
                 "message": "This was the final approval. The post has been sent to all stakeholders.",
                 "post": post},
            )

        next_level = workflow.current_level(post)
        next_approver = get_approver_for_level(next_level)
        if not next_approver:
            db.commit()
            return templates.TemplateResponse(
                "result.html",
                {"request": request, "title": "Approval recorded",
                 "message": f"Approved at {token.level}, but no approver configured for {next_level}.",
                 "post": post},
            )

        approve_tok = workflow.create_action_token(db, post, next_level, next_approver.email)
        reject_tok = workflow.create_action_token(db, post, next_level, next_approver.email)
        db.commit()

        try:
            email_service.send_approval_request(
                to_email=next_approver.email,
                approver_name=next_approver.name,
                level=next_level,
                post_content=post.content,
                submitter_name=post.submitter_name,
                submitter_email=post.submitter_email,
                submitter_role=post.submitter_role,
                approve_token=approve_tok,
                reject_token=reject_tok,
            )
        except Exception:
            logger.exception("Failed sending approval request to %s", next_approver.email)

        return templates.TemplateResponse(
            "result.html",
            {"request": request, "title": "Approval recorded",
             "message": f"Approved at {token.level}. Forwarded to {next_level} for review.",
             "post": post},
        )

    elif action.upper() == "REJECT":
        workflow.record_rejection(db, post, token.level, token.approver_email, comment)
        db.commit()

        try:
            email_service.send_rejection_notice(
                to_email=post.submitter_email,
                submitter_name=post.submitter_name,
                post_content=post.content,
                rejected_by_level=token.level,
                rejected_by_email=token.approver_email,
                reason=comment,
            )
        except Exception:
            logger.exception("Failed sending rejection notice to %s", post.submitter_email)

        return templates.TemplateResponse(
            "result.html",
            {"request": request, "title": "Rejection recorded",
             "message": f"Post rejected at {token.level}. The submitter has been notified.",
             "post": post},
        )

    raise HTTPException(status_code=400, detail="Invalid action.")