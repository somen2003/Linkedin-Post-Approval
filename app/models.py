import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Post(Base):
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=_uuid)
    content = Column(Text, nullable=False)

    submitter_name = Column(String, nullable=False)
    submitter_email = Column(String, nullable=False, index=True)
    submitter_role = Column(String, nullable=False)

    approval_chain = Column(JSON, nullable=False)  # e.g. ["L2", "L3"]
    current_step = Column(Integer, default=0, nullable=False)
    status = Column(String, default="PENDING", nullable=False)  # PENDING / APPROVED / REJECTED

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    logs = relationship("ApprovalLog", back_populates="post", cascade="all, delete-orphan")
    tokens = relationship("ApprovalToken", back_populates="post", cascade="all, delete-orphan")


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id = Column(String, primary_key=True, default=_uuid)
    post_id = Column(String, ForeignKey("posts.id"), nullable=False, index=True)
    level = Column(String, nullable=False)
    approver_email = Column(String, nullable=False)
    action = Column(String, nullable=False)  # APPROVED / REJECTED
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    post = relationship("Post", back_populates="logs")


class ApprovalToken(Base):
    __tablename__ = "approval_tokens"

    token_hash = Column(String, primary_key=True)
    post_id = Column(String, ForeignKey("posts.id"), nullable=False, index=True)
    level = Column(String, nullable=False)
    approver_email = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    post = relationship("Post", back_populates="tokens")
