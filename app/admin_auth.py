import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

_security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    ok_user = secrets.compare_digest(credentials.username.encode(), settings.admin_username.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), settings.admin_password.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized.",
            headers={"WWW-Authenticate": 'Basic realm="Admin Dashboard"'},
        )
    return credentials.username
