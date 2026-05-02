import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.services.auth import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


def _set_auth_cookies(response: Response, access: str, refresh: str, secure: bool) -> None:
    settings = get_settings()
    response.set_cookie(
        "access_token",
        access,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_ttl_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.refresh_token_ttl_days * 86400,
        path="/auth/refresh",
    )


def _is_secure_request(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "")
    if forwarded.lower() == "https":
        return True
    return request.url.scheme == "https"


@router.post("/login", response_model=LoginResponse)
@limiter.limit(get_settings().login_rate_limit)
def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    user = db.execute(
        select(User).where(User.email == body.email)
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials"
        )

    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)
    _set_auth_cookies(response, access, refresh, secure=_is_secure_request(request))

    return LoginResponse(
        user_id=user.id, name=user.name, email=user.email, role=user.role.value
    )


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        # Fall back to header for non-browser clients
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[len("Bearer ") :]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="no refresh token"
        )

    try:
        payload = decode_token(token, expected_type="refresh")
        user_id = uuid.UUID(payload["sub"])
    except (TokenError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token"
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found"
        )

    new_access = create_access_token(user.id, user.role)
    new_refresh = create_refresh_token(user.id)
    _set_auth_cookies(response, new_access, new_refresh, secure=_is_secure_request(request))
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(
        id=user.id, name=user.name, email=user.email, role=user.role.value
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")
    return {"ok": True}
