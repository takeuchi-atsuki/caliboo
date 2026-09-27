"""セッション(ログイン状態)の発行・検証・破棄。

!NOTE: トークンは平文でDBへ保存しない。sha256でハッシュ化した値のみ`user_sessions
       .token_hash`に保存し、DBが漏えいしても有効なセッションを乗っ取られないようにする。
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from caliboo_api.models import User, UserSession
from caliboo_api.extension_models import AccountState

COOKIE_NAME = "caliboo_session"
SESSION_LIFETIME = timedelta(hours=12)
SESSION_MAX_AGE_SECONDS = int(SESSION_LIFETIME.total_seconds())


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cleanup_expired_sessions(session: Session) -> None:
    """期限切れセッション行を削除する。

    !NOTE: 掃除はログイン時にまとめて行う(ここでしか呼ばない)。全リクエストの
           たびにDELETEを走らせるコストを避けるため。
    """
    now = _now()
    for row in session.query(UserSession).all():
        if datetime.fromisoformat(row.expires_at) < now:
            session.delete(row)


def create_session(session: Session, user: User) -> str:
    """新しいセッションを発行し、生トークンを返す(DBにはハッシュ値のみ保存する)。"""
    _cleanup_expired_sessions(session)

    token = secrets.token_urlsafe(32)
    now = _now()
    session.add(
        UserSession(
            token_hash=_hash_token(token),
            user_id=user.id,
            created_at=now.isoformat(),
            expires_at=(now + SESSION_LIFETIME).isoformat(),
        )
    )
    return token


def get_user_for_token(session: Session, token: str) -> User | None:
    """トークンから有効なセッションを引き、紐づくユーザーを返す。期限切れ・不明なら`None`。"""
    row = session.get(UserSession, _hash_token(token))
    if row is None:
        return None
    if datetime.fromisoformat(row.expires_at) < _now():
        return None
    state = session.get(AccountState, row.user_id)
    if state is not None and not state.active:
        return None
    return session.get(User, row.user_id)


def delete_session(session: Session, token: str) -> None:
    """セッション行を削除する(存在しなくてもエラーにしない=ログアウトの冪等性)。"""
    row = session.get(UserSession, _hash_token(token))
    if row is not None:
        session.delete(row)
