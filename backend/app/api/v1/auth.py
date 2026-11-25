from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import enforce_auth_rate_limit, get_current_user, require_csrf_origin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.services.auth_service import (
    authenticate_user,
    create_user_session,
    register_user,
    revoke_session_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
    __: None = Depends(require_csrf_origin),
) -> AuthResponse:
    try:
        user = register_user(
            db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            is_admin=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    raw_token, _ = create_user_session(
        db, user=user, user_agent=request.headers.get("user-agent")
    )
    _set_session_cookie(response, raw_token)
    return AuthResponse(user=UserResponse.model_validate(user), message="Registration successful.")


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
    __: None = Depends(require_csrf_origin),
) -> AuthResponse:
    user = authenticate_user(db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    raw_token, _ = create_user_session(
        db, user=user, user_agent=request.headers.get("user-agent")
    )
    _set_session_cookie(response, raw_token)
    return AuthResponse(user=UserResponse.model_validate(user), message="Signed in successfully.")


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf_origin),
) -> dict:
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token:
        revoke_session_token(db, raw_token)
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return {"message": "Signed out."}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.delete("/account")
def delete_my_account(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token:
        revoke_session_token(db, raw_token)
    db.delete(current_user)
    db.commit()
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return {"message": "Your account and personal profile data have been permanently deleted."}
