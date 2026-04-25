import hashlib
import secrets


def generate_token() -> str:
    """Generate a cryptographically secure URL-safe token (~43 chars)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token with SHA-256 for safe DB storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
