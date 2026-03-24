import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import User
from millicall.infrastructure.audit import audit_log
from millicall.infrastructure.database import get_session
from millicall.infrastructure.repositories.user_repo import UserRepository
from millicall.presentation.auth import (
    create_access_token,
    get_current_user,
    verify_password,
)
from millicall.presentation.schemas import LoginRequest, TokenResponse, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Simple in-memory rate limiter for login attempts
_login_attempts: dict[str, list[float]] = defaultdict(list)
_LOGIN_WINDOW = 300  # 5 minutes
_LOGIN_MAX_ATTEMPTS = 10  # max attempts per window


def _check_rate_limit(client_ip: str) -> None:
    """Raise 429 if client has exceeded login attempt limit."""
    now = time.monotonic()
    # Prune old entries
    _login_attempts[client_ip] = [
        t for t in _login_attempts[client_ip] if now - t < _LOGIN_WINDOW
    ]
    if len(_login_attempts[client_ip]) >= _LOGIN_MAX_ATTEMPTS:
        logger.warning("Rate limit exceeded for login from %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(_LOGIN_WINDOW)},
        )
    _login_attempts[client_ip].append(now)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    repo = UserRepository(session)
    user = await repo.get_by_username(data.username)
    if not user or not verify_password(data.password, user.hashed_password):
        audit_log(
            action="auth.login_failed",
            actor=data.username,
            client_ip=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    audit_log(
        action="auth.login",
        actor=data.username,
        client_ip=client_ip,
    )
    access_token = create_access_token(data={"sub": user.username}, role=user.role)

    # Set HttpOnly cookie
    response.set_cookie(
        key="millicall_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=int(60 * 1440),  # match JWT expiry
        path="/",
    )

    # Also return token in body for backward compatibility
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        is_admin=current_user.is_admin,
        role=current_user.role,
    )


@router.post("/logout")
async def logout(response: Response):
    """Clear the HttpOnly auth cookie."""
    response.delete_cookie(key="millicall_token", path="/")
    return {"ok": True}
