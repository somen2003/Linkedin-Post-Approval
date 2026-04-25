from datetime import datetime

from pydantic import BaseModel


class ApprovalLogOut(BaseModel):
    level: str
    approver_email: str
    action: str
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PostOut(BaseModel):
    id: str
    content: str
    submitter_name: str
    submitter_email: str
    submitter_role: str
    approval_chain: list[str]
    current_step: int
    status: str
    created_at: datetime
    updated_at: datetime
    logs: list[ApprovalLogOut] = []

    model_config = {"from_attributes": True}
