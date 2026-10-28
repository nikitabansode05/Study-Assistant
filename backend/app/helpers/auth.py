"""Minimal mentor authorization for the LOCAL PROTOTYPE.

How it works
------------
* One hardcoded mentor account (see config.py / backend/.env).
* POST /auth/login checks the credentials and returns a random session token.
* The token is kept ONLY in this process's memory (no database, no JWT, no
  cookies). Restarting the backend logs every mentor out.
* The React app keeps the token in component state only, so reloading the page
  also returns to the unauthenticated student view.
* Protected routes depend on ``require_mentor`` and expect the header
  ``Authorization: Bearer <token>``.

This is NOT production-grade security: credentials are hardcoded, there is no
rate limiting, and traffic is plain HTTP. It simply prevents casual,
unauthenticated clients from calling upload/import/delete routes directly.
"""

import secrets
import threading
import time

from fastapi import Header, HTTPException

from ..config import MENTOR_PASSWORD, MENTOR_SESSION_HOURS, MENTOR_USER_ID

_sessions: dict[str, dict] = {}
_lock = threading.Lock()


async def _purge_expired(now: float) -> None:
    for token in [t for t, s in _sessions.items() if s["expires_at"] <= now]:
        _sessions.pop(token, None)


async def check_credentials(user_id: str, password: str) -> bool:
    # Case-insensitive user ID (it is an e-mail address); exact password.
    user_ok = secrets.compare_digest(user_id.strip().lower().encode(), MENTOR_USER_ID.strip().lower().encode())
    pass_ok = secrets.compare_digest(password.encode(), MENTOR_PASSWORD.encode())
    return user_ok and pass_ok


async def create_session(user_id: str) -> dict:
    now = time.time()
    token = secrets.token_urlsafe(32)
    session = {"user_id": user_id, "role": "mentor", "expires_at": now + MENTOR_SESSION_HOURS * 3600}
    with _lock:
        await _purge_expired(now)
        _sessions[token] = session
    return {"token": token, **session}


async def revoke_session(token: str | None) -> bool:
    if not token:
        return False
    with _lock:
        return _sessions.pop(token, None) is not None


async def _token_from_header(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


async def get_session(authorization: str | None) -> dict | None:
    token = _token_from_header(authorization)
    if not token:
        return None
    now = time.time()
    with _lock:
        _purge_expired(now)
        session = _sessions.get(token)
    return {"token": token, **session} if session else None


def require_mentor(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI dependency for mentor-only routes."""
    session = get_session(authorization)
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Mentor login required. Please log in as the mentor (sessions end when the backend restarts).",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session
