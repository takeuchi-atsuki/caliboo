"""SQLiteとPostgreSQLの業務更新に共通の方言境界。"""

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from caliboo_api.models import User


def conflict_insert(session: Session, table):
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        return pg_insert(table)
    if dialect == "sqlite":
        return sqlite_insert(table)
    raise RuntimeError("unsupported database dialect")


def lock_user(session: Session, user_id: int) -> None:
    """共有DBでは同一ユーザーの複合業務更新を直列化する(他ユーザーは独立)。"""
    if session.get_bind().dialect.name == "postgresql":
        session.query(User).filter_by(id=user_id).populate_existing().with_for_update(
            key_share=True,
        ).one()


def lock_attempt_source(session: Session, source: str, reset: bool = False) -> None:
    """接続元ごとの失敗回数確認と記録を共有DB上でも同じトランザクションにまとめる。"""
    if session.get_bind().dialect.name == "postgresql":
        namespace = "reset" if reset else "login"
        session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 25))"),
                        {"key": namespace + ":" + source})
