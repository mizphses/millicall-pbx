from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.config import settings
from millicall.domain.models import User
from millicall.infrastructure.database import get_session
from millicall.infrastructure.repositories.user_repo import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(data: dict, role: str = "admin") -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiry_minutes)
    to_encode.update({"exp": expire, "role": role})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Prefer Authorization header, fall back to HttpOnly cookie
    effective_token = token or request.cookies.get(settings.session_cookie_name)
    if not effective_token:
        raise credentials_exception

    try:
        payload = jwt.decode(effective_token, settings.jwt_secret, algorithms=["HS256"])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as err:
        raise credentials_exception from err

    repo = UserRepository(session)
    user = await repo.get_by_username(username)
    if user is None:
        raise credentials_exception
    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that ensures the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return current_user
