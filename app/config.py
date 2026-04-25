from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # SMTP
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_email: str = "approvals@example.com"
    smtp_from_name: str = "LinkedIn Approvals"

    # App
    base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./data.db"
    action_token_expiry_days: int = 7

    # Admin dashboard credentials (HTTP Basic Auth).
    admin_username: str = "admin"
    admin_password: str = "change_me"

    # Workflow levels (ordered). Add L4, L5, etc. here to extend.
    approval_levels: list[str] = ["L1", "L2", "L3"]


settings = Settings()


@dataclass(frozen=True)
class Employee:
    name: str
    email: str
    role: str  # "L1" | "L2" | "L3" | "OTHER"


# Edit this list to add, remove, or change people. That's the only place to edit.
EMPLOYEES: list[Employee] = [
    Employee(name="Somen Mishra",        email="somenmishra333@gmail.com",     role="L1"),
    Employee(name="Sthitapragnya Sahoo", email="sthitapragnya780@gmail.com",   role="L2"),
    Employee(name="Surya Pratap",        email="agenticsurya@gmail.com",       role="L3"),
    Employee(name="Suvam Sen",           email="suvamsen172420@gmail.com",     role="OTHER"),
    Employee(name="Tapan Das",           email="tapankumarpanda164@gmail.com", role="OTHER"),
]


def get_employee_by_name(name: str) -> Employee | None:
    for emp in EMPLOYEES:
        if emp.name == name:
            return emp
    return None


def get_approver_for_level(level: str) -> Employee | None:
    for emp in EMPLOYEES:
        if emp.role == level:
            return emp
    return None


def get_all_approvers() -> list[Employee]:
    result = []
    for lvl in settings.approval_levels:
        emp = get_approver_for_level(lvl)
        if emp:
            result.append(emp)
    return result
