"""初期管理者を対話作成する: python3 -m caliboo_api.manage。"""

import argparse
import getpass
import os

from caliboo_api.auth.password import hash_password
from caliboo_api.config import get_settings
from caliboo_api.data.account_data import initialize_profile, now_iso
from caliboo_api.db import prepare_runtime, session_scope
from caliboo_api.extension_models import AccountState
from caliboo_api.models import User
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login-id", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()
    if not args.login_id.strip() or not args.display_name.strip():
        parser.error("login-id and display-name must not be empty")
    password = getpass.getpass("Password (12-128 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12 or len(password) > 128 or password != confirmation:
        parser.error("password must match and contain 12-128 characters")
    # !NOTE: 初期管理コマンドはデモユーザーを作らない。秘密値を引数に受け取らない。
    previous = os.environ.get("CALIBOO_DEMO_SEED")
    os.environ["CALIBOO_DEMO_SEED"] = "false"
    try:
        prepare_runtime(get_settings())
    finally:
        if previous is None:
            os.environ.pop("CALIBOO_DEMO_SEED", None)
        else:
            os.environ["CALIBOO_DEMO_SEED"] = previous
    with session_scope() as session:
        if session.query(User).filter_by(login_id=args.login_id.strip()).first():
            parser.error("login id already exists")
        user = User(
            login_id=args.login_id.strip(),
            display_name=args.display_name.strip(),
            role="admin",
            password_hash=hash_password(password),
            created_at=now_iso(),
        )
        session.add(user)
        try:
            session.flush()
            initialize_profile(session, user.id)
            session.add(AccountState(user_id=user.id, active=True))
            session.commit()
        except IntegrityError:
            session.rollback()
            parser.error("login id or related data already exists")
    print("管理者を作成しました。")


if __name__ == "__main__":
    try:
        main()
    except SQLAlchemyError:
        raise SystemExit("DB管理処理に失敗しました。DB設定を確認してください。") from None
