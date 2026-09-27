"""アプリ設定。

!NOTE: SQLiteのデフォルト保存先はCWD非依存の絶対パス(`backend/var/caliboo.db`)にしている。
       uvicornの起動ディレクトリによらず常に同じ場所を指すようにするため。

!NOTE: `CALIBOO_COOKIE_SECURE`の既定はfalse(Cookieの`Secure`属性を付けない)。開発環境は
       httpで動かすため、既定でtrueにすると開発時にCookieが送られなくなってしまう。
       本番相当のhttps環境では環境変数で有効化する想定。
"""

import os
from pathlib import Path

_DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent.parent.parent / "var" / "caliboo.db"

_TRUE_VALUES = {"1", "true"}


def _parse_bool_env(value: str | None) -> bool:
    return value is not None and value.strip().lower() in _TRUE_VALUES


class Settings:
    def __init__(self, sqlite_path: str, cookie_secure: bool) -> None:
        self.sqlite_path = sqlite_path
        self.cookie_secure = cookie_secure


def get_settings() -> Settings:
    sqlite_path = os.environ.get("CALIBOO_SQLITE_PATH", str(_DEFAULT_SQLITE_PATH))
    cookie_secure = _parse_bool_env(os.environ.get("CALIBOO_COOKIE_SECURE"))
    return Settings(sqlite_path=sqlite_path, cookie_secure=cookie_secure)
