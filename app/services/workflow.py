from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Post, ApprovalLog, ApprovalToken
from app.services.tokens import generate_token, hash_token


def build_chain(submitter_role: str) -> list[str]:
    """Build the approval chain, skipping the submitter's level if they are L1/L2/L3."""
    levels = list(settings.approval_levels)
    if submitter_role in levels:
        return [lvl for lvl in levels if lvl != submitter_role]
    return levels


def current_level(post: Post) -> str | None:
    """Return the level currently expected to approve, or None if chain is done."""
    if post.current_step >= len(post.approval_chain):
        return None
    return post.approval_chain[post.current_step]


def create_action_token(db: Session, post: Post, level: str, approver_email: str) -> str:
    """Generate a one-time action token bound to post + level + approver."""
    raw = generate_token()
    token = ApprovalToken(
        token_hash=hash_token(raw),
        post_id=post.id,
        level=level,
        approver_email=approver_email,
        expires_at=datetime.utcnow() + timedelta(days=settings.action_token_expiry_days),
    )
    db.add(token)
    return raw


def record_approval(db: Session, post: Post, level: str, approver_email: str, comment: str | None) -> None:
    """Record an approval and advance the chain."""
    db.add(ApprovalLog(
        post_id=post.id,
        level=level,
        approver_email=approver_email,
        action="APPROVED",
        comment=comment,
    ))
    post.current_step += 1
    if post.current_step >= len(post.approval_chain):
        post.status = "APPROVED"


def record_rejection(db: Session, post: Post, level: str, approver_email: str, comment: str | None) -> None:
    """Record a rejection and terminate the workflow."""
    db.add(ApprovalLog(
        post_id=post.id,
        level=level,
        approver_email=approver_email,
        action="REJECTED",
        comment=comment,
    ))
    post.status = "REJECTED"


def consume_action_token(db: Session, raw_token: str) -> tuple[ApprovalToken | None, str | None]:
    """Validate an action token. Returns (token, error_message). Does not mark as used."""
    token = db.query(ApprovalToken).filter(ApprovalToken.token_hash == hash_token(raw_token)).first()
    if not token:
        return None, "Invalid or unknown token."
    if token.used_at is not None:
        return None, "This approval link has already been used."
    if token.expires_at < datetime.utcnow():
        return None, "This approval link has expired."
    return token, None
