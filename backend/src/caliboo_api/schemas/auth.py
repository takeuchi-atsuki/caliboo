from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

Role = Literal["admin", "member"]

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# !NOTE: パスワードは前後空白をstripしない(min_lengthのみ)。stripすると、利用者が
#        意図して先頭・末尾に空白を含めたパスワードを設定していた場合に、別の値として
#        扱われてしまう(=正しいパスワードなのにログインできなくなる)ため。
NonEmptyRawText = Annotated[str, StringConstraints(min_length=1)]


class LoginRequest(BaseModel):
    """`POST /api/auth/login`のリクエストボディ。"""

    loginId: NonEmptyText
    password: NonEmptyRawText


class CurrentUser(BaseModel):
    """ログイン中のユーザー(`login`・`logout`・`me`共通のレスポンス形状)。"""

    id: int
    loginId: str
    displayName: str
    role: Role
