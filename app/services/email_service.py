import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def _render(template_name: str, **context) -> str:
    return _env.get_template(template_name).render(**context)


def _send(to_email: str, subject: str, html_body: str) -> None:
    msg = EmailMessage()
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content("Your email client does not support HTML. Please view in an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        logger.info("Sent email to %s: %s", to_email, subject)
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        raise


def send_approval_request(
    *,
    to_email: str,
    approver_name: str,
    level: str,
    post_content: str,
    submitter_name: str,
    submitter_email: str,
    submitter_role: str,
    approve_token: str,
    reject_token: str,
) -> None:
    subject = f"[Approval {level}] LinkedIn post from {submitter_name}"
    html = _render(
        "approval_request.html",
        approver_name=approver_name,
        level=level,
        post_content=post_content,
        submitter_name=submitter_name,
        submitter_email=submitter_email,
        submitter_role=submitter_role,
        approve_url=f"{settings.base_url}/approve/{approve_token}",
        reject_url=f"{settings.base_url}/reject/{reject_token}",
    )
    _send(to_email, subject, html)


def send_final_approved(
    *,
    to_email: str,
    recipient_name: str,
    post_content: str,
    submitter_name: str,
    submitter_email: str,
    approval_trail: list[dict],
) -> None:
    subject = f"[Approved] LinkedIn post from {submitter_name}"
    html = _render(
        "final_approved.html",
        recipient_name=recipient_name,
        post_content=post_content,
        submitter_name=submitter_name,
        submitter_email=submitter_email,
        approval_trail=approval_trail,
    )
    _send(to_email, subject, html)


def send_rejection_notice(
    *,
    to_email: str,
    submitter_name: str,
    post_content: str,
    rejected_by_level: str,
    rejected_by_email: str,
    reason: str | None,
) -> None:
    subject = "[Rejected] Your LinkedIn post was not approved"
    html = _render(
        "rejected.html",
        submitter_name=submitter_name,
        post_content=post_content,
        rejected_by_level=rejected_by_level,
        rejected_by_email=rejected_by_email,
        reason=reason,
    )
    _send(to_email, subject, html)
