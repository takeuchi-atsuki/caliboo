"""アプリ設定。

!NOTE: SQLiteのデフォルト保存先はCWD非依存の絶対パス(`backend/var/caliboo.db`)にしている。
       uvicornの起動ディレクトリによらず常に同じ場所を指すようにするため。

!NOTE: `CALIBOO_COOKIE_SECURE`の既定はfalse(Cookieの`Secure`属性を付けない)。開発環境は
       httpで動かすため、既定でtrueにすると開発時にCookieが送られなくなってしまう。
       本番相当のhttps環境では環境変数で有効化する想定。
"""

import os
from pathlib import Path

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

_DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent.parent.parent / "var" / "caliboo.db"

_TRUE_VALUES = {"1", "true"}


def _parse_bool_env(value: str | None) -> bool:
    return value is not None and value.strip().lower() in _TRUE_VALUES


class Settings:
    def __init__(
        self, sqlite_path: str, cookie_secure: bool, database_url: URL | None = None,
    ) -> None:
        self.sqlite_path = sqlite_path
        self.cookie_secure = cookie_secure
        self.database_url = database_url


def parse_database_url(value: str) -> URL:
    """明示された共有DB設定を検証する。誤設定時にSQLiteへ戻さない。"""
    try:
        url = make_url(value)
    except (ArgumentError, ValueError):
        raise ValueError("CALIBOO_DATABASE_URL is not a valid PostgreSQL URL") from None
    if url.drivername not in {"postgresql", "postgresql+psycopg"} or not url.database:
        raise ValueError("CALIBOO_DATABASE_URL must identify a PostgreSQL database")
    return url.set(drivername="postgresql+psycopg")


def get_settings() -> Settings:
    sqlite_path = os.environ.get("CALIBOO_SQLITE_PATH", str(_DEFAULT_SQLITE_PATH))
    cookie_secure = _parse_bool_env(os.environ.get("CALIBOO_COOKIE_SECURE"))
    configured = os.environ.get("CALIBOO_DATABASE_URL")
    database_url = parse_database_url(configured) if configured is not None else None
    return Settings(sqlite_path=sqlite_path, cookie_secure=cookie_secure,
                    database_url=database_url)
