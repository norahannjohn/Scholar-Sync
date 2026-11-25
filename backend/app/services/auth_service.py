from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    needs_rehash,
    verify_password,
)
from app.models.user import StudentProfile, User, UserSession, utcnow


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
    is_admin: bool = False,
) -> User:
    norm_email = normalize_email(email)
    existing = db.scalar(select(User).where(User.email == norm_email))
    if existing:
        raise ValueError("An account with this email already exists.")

    user = User(
        email=norm_email,
        password_hash=hash_password(password),
        full_name=full_name.strip() if full_name else None,
        is_active=True,
        is_admin=is_admin,
    )
    db.add(user)
    db.flush()

    profile = StudentProfile(
        user_id=user.id,
        display_name=user.full_name,
        consent_matching=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    norm_email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == norm_email))
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.add(user)
        db.commit()
    return user


def create_user_session(
    db: Session, *, user: User, user_agent: str | None = None
) -> tuple[str, UserSession]:
    settings = get_settings()
    raw_token = generate_session_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        user_agent=(user_agent or "")[:255] or None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return raw_token, session


def get_user_by_session_token(db: Session, raw_token: str) -> User | None:
    if not raw_token:
        return None
    token_hash = hash_session_token(raw_token)
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
    )
    if not session:
        return None
    now = utcnow()
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        from datetime import UTC

        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        return None
    user = db.scalar(select(User).where(User.id == session.user_id, User.is_active.is_(True)))
    return user


def revoke_session_token(db: Session, raw_token: str) -> None:
    if not raw_token:
        return
    token_hash = hash_session_token(raw_token)
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()
        db.add(session)
        db.commit()


def ensure_initial_admin_from_env(db: Session) -> bool:
    """Create initial admin if ADMIN_EMAIL & ADMIN_INITIAL_PASSWORD are set and no admin exists."""
    settings = get_settings()
    if not settings.admin_email or not settings.admin_initial_password:
        return False
    existing_admin = db.scalar(select(User).where(User.is_admin.is_(True)).limit(1))
    if existing_admin:
        return False
    norm_email = normalize_email(settings.admin_email)
    existing_user = db.scalar(select(User).where(User.email == norm_email))
    if existing_user:
        existing_user.is_admin = True
        db.add(existing_user)
        db.commit()
        return True
    register_user(
        db,
        email=norm_email,
        password=settings.admin_initial_password,
        full_name=settings.admin_full_name,
        is_admin=True,
    )
    return True
