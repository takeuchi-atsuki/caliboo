"""認証・認可の依存関数(FastAPIの`Depends`で使う)。"""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from caliboo_api.auth.session import COOKIE_NAME, get_user_for_token
from caliboo_api.db import get_session
from caliboo_api.models import User


def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:
    """Cookieのセッショントークンからログイン中のユーザーを取得する。

    Cookieが無い・トークンが不明・期限切れのいずれも401(区別しない。存在有無を
    第三者に推測させないため)。
    """
    token = request.cookies.get(COOKIE_NAME)
    user = get_user_for_token(session, token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """`role == "admin"`(講師)のみ許可する。それ以外は403。"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
    return user


def require_member(user: User = Depends(get_current_user)) -> User:
    """`role == "member"`(新入社員)のみ許可する。それ以外は403。"""
    if user.role != "member":
        raise HTTPException(status_code=403, detail="forbidden")
    return user
