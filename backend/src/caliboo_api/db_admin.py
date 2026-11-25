"""共有DBの初期化・SQLiteスナップショット・1DB移行・検証。"""

import argparse
from pathlib import Path
import sqlite3

from sqlalchemy.exc import SQLAlchemyError

from caliboo_api.config import get_settings
from caliboo_api.db import initialize_shared_db
from caliboo_api.migration import migrate_sqlite, snapshot_sqlite, verify_migration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--demo", action="store_true")
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--source", type=Path, required=True)
    snapshot.add_argument("--output", type=Path, required=True)
    for name in ("migrate", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "snapshot":
            snapshot_sqlite(args.source, args.output)
            print("SQLiteスナップショットを作成しました。")
            return
        url = get_settings().database_url
        if url is None:
            parser.error("CALIBOO_DATABASE_URL is required for shared database operations")
        if args.command == "init":
            initialize_shared_db(url, demo=args.demo)
            print("共有DBを初期化しました。")
            return
        operation = migrate_sqlite if args.command == "migrate" else verify_migration
        counts = operation(args.snapshot, url)
        print(f"検証成功: {len(counts)} テーブル / {sum(counts.values())} 行")
    except (SQLAlchemyError, sqlite3.Error, OSError, ValueError):
        # !NOTE: DB接続文字列、レコード、SQLの内容は表示しない。
        parser.exit(1, "DB管理処理に失敗しました。DB設定・スナップショットを確認してください。\n")
    except RuntimeError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
