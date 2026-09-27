"""認証API(ログイン・ログアウト・現在ユーザー取得)。

!NOTE: このルーターだけは`main.py`で`Depends(get_current_user)`を一括付与しない
       (ログイン前に呼ぶ必要があるため)。`me`はエンドポイント自身が
       `Depends(get_current_user)`を宣言して認証を要求する。
"""

import math
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from caliboo_api.auth import password
from caliboo_api.auth.deps import get_current_user
from caliboo_api.auth.session import (
    COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    create_session,
    delete_session,
)
from caliboo_api.config import get_settings
from caliboo_api.db import get_session
from caliboo_api.models import HomeProfile, User
from caliboo_api.extension_models import LoginAttempt
from caliboo_api.data.account_data import is_active
from caliboo_api.schemas.auth import CurrentUser, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_current_user(user: User, session: Session) -> CurrentUser:
    profile = session.query(HomeProfile).filter_by(user_id=user.id).first()
    return CurrentUser(
        id=user.id, loginId=user.login_id, displayName=user.display_name, role=user.role,
        streakDays=profile.user_streak_days if profile else 0,
    )


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
    )


@router.post("/login", response_model=CurrentUser)
def login(
    payload: LoginRequest, request: Request, response: Response,
    session: Session = Depends(get_session)
) -> CurrentUser:
    """ログインID・パスワードを検証し、成功時はセッションCookieを発行する。

    !NOTE: ログインIDが存在しない場合、またはユーザーは存在するが`password_hash`が
           `None`(SSO移行後等、パスワード未設定のアカウント)の場合も、ダミーハッシュ
           (`password.DUMMY_PASSWORD_HASH`)で`verify_password()`を呼ぶ。応答時間の差から
           ログインIDの存在有無が推測されないようにするため。失敗理由(ID誤り/パスワード誤り/
           パスワード未設定)も区別しない。
    """
    # !NOTE: X-Forwarded-Forは信頼しない。プロキシ運用では信頼済み接続元の設定が必要。
    source = request.client.host if request.client else "unknown"
    now = int(time.time())
    session.query(LoginAttempt).filter(LoginAttempt.attempted_at <= now - 900).delete()
    attempts = session.query(LoginAttempt).filter_by(source=source).order_by(
        LoginAttempt.attempted_at).all()
    if len(attempts) >= 20:
        retry = max(1, math.ceil(attempts[0].attempted_at + 900 - now))
        session.commit()
        raise HTTPException(429, "too many login attempts", headers={"Retry-After": str(retry)})
    user = session.query(User).filter(User.login_id == payload.loginId).first()
    has_password = user is not None and user.password_hash
    password_hash = user.password_hash if has_password else password.DUMMY_PASSWORD_HASH
    password_is_valid = password.verify_password(payload.password, password_hash)

    if user is None or not password_is_valid or not is_active(session, user.id):
        session.add(LoginAttempt(source=source, attempted_at=now))
        session.commit()
        raise HTTPException(status_code=401, detail="invalid login id or password")

    token = create_session(session, user)
    session.commit()
    _set_session_cookie(response, token)
    return _to_current_user(user, session)


@router.post("/logout", status_code=204)
def logout(
    request: Request, response: Response, session: Session = Depends(get_session)
) -> Response:
    """セッションを破棄しCookieを削除する。

    認証不要・冪等にする(Cookieが無い・無効・期限切れのいずれでも204で成功させる)。
    期限切れのセッションでログアウトした場合に401を返すと、画面側がエラー扱いか
    成功扱いかの判断が必要になるため。
    """
    token = request.cookies.get(COOKIE_NAME)
    if token:
        delete_session(session, token)
        session.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=CurrentUser)
def me(user: User = Depends(get_current_user),
       session: Session = Depends(get_session)) -> CurrentUser:
    return _to_current_user(user, session)
