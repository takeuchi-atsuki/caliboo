"""講師向けユーザー管理API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from caliboo_api.auth.deps import require_admin
from caliboo_api.auth.password import hash_password
from caliboo_api.data.account_data import (
    account_view, initialize_profile, now_iso, set_department,
)
from caliboo_api.db import get_session
from caliboo_api.extension_models import AccountState
from caliboo_api.models import User, UserSession
from caliboo_api.schemas.auth import Role

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    loginId: Text
    displayName: Text
    password: Password
    role: Role = "member"
    departmentId: str | None = None


class UserUpdate(BaseModel):
    displayName: Text
    role: Role
    active: bool
    departmentId: str | None = None
    password: Password | None = None


@router.get("")
def list_users(departmentId: str | None = None, session: Session = Depends(get_session),
               _admin: User = Depends(require_admin)) -> dict:
    users = [account_view(session, user) for user in session.query(User).order_by(User.id)]
    return {"users": [user for user in users
                      if departmentId is None or user["departmentId"] == departmentId]}


@router.post("", status_code=201)
def create_user(payload: UserCreate, session: Session = Depends(get_session),
                admin: User = Depends(require_admin)) -> dict:
    user = User(login_id=payload.loginId, display_name=payload.displayName, role=payload.role,
                password_hash=hash_password(payload.password), created_at=now_iso())
    session.add(user)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "login id already exists") from None
    initialize_profile(session, user.id)
    set_department(session, user.id, payload.departmentId, admin.id)
    session.commit()
    return account_view(session, user)


@router.post("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, session: Session = Depends(get_session),
                admin: User = Depends(require_admin)) -> dict:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    if user_id == admin.id and (not payload.active or payload.role != "admin"):
        raise HTTPException(409, "cannot disable or demote yourself")
    set_department(session, user_id, payload.departmentId, admin.id)
    state = session.get(AccountState, user_id)
    state.active = payload.active
    user.display_name = payload.displayName
    if payload.password is not None or not payload.active or user.role != payload.role:
        session.query(UserSession).filter_by(user_id=user_id).delete()
    user.role = payload.role
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    session.commit()
    return account_view(session, user)
