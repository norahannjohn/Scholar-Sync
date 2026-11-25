from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import rate_limiter, verify_origin_header
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_session_token


def require_csrf_origin(request: Request) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    settings = get_settings()
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    host = request.headers.get("host")
    if not verify_origin_header(origin, referer, settings.allowed_origins, host):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin verification failed.",
        )


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    return get_user_by_session_token(db, token)


def get_current_user(
    request: Request,
    user: User | None = Depends(get_optional_user),
    _: None = Depends(require_csrf_origin),
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user


def get_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return user


def enforce_auth_rate_limit(request: Request) -> None:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = rate_limiter.check(
        f"auth:{client_ip}",
        max_requests=settings.auth_rate_limit_per_minute,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many authentication attempts. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )


def enforce_assistant_rate_limit(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    settings = get_settings()
    allowed, retry_after = rate_limiter.check(
        f"assistant:{user.id}",
        max_requests=settings.assistant_rate_limit_per_minute,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Assistant rate limit exceeded. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )
