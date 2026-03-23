from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import User
from millicall.infrastructure.database import get_session
from millicall.infrastructure.repositories.user_repo import UserRepository
from millicall.presentation.auth import (
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from millicall.presentation.schemas import (
    ChangePasswordRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    repo = UserRepository(session)
    users = await repo.get_all()
    return [
        UserResponse(id=u.id, username=u.username, display_name=u.display_name, is_admin=u.is_admin)
        for u in users
    ]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    repo = UserRepository(session)
    existing = await repo.get_by_username(data.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    user = await repo.create(
        User(
            username=data.username,
            hashed_password=hash_password(data.password),
            display_name=data.display_name,
            is_admin=data.is_admin,
        )
    )
    return UserResponse(
        id=user.id, username=user.username, display_name=user.display_name, is_admin=user.is_admin
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await repo.update(user_id, display_name=data.display_name, is_admin=data.is_admin)
    user = await repo.get_by_id(user_id)
    return UserResponse(
        id=user.id, username=user.username, display_name=user.display_name, is_admin=user.is_admin
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    admin_count = len([u for u in await repo.get_all() if u.is_admin])
    if user.is_admin and admin_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin")
    await repo.delete(user_id)


@router.put("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    user_id: int,
    data: ChangePasswordRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Admin resets another user's password, or user changes own password."""
    repo = UserRepository(session)
    target = await repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    # Self: must verify current password. Admin for others: current_password is admin's own password.
    if current_user.id == user_id:
        if not verify_password(data.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
    else:
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
        if not verify_password(data.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Admin password is incorrect")
    await repo.update(user_id, hashed_password=hash_password(data.new_password))
