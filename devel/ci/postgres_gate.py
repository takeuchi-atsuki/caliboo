"""#25候補で隔離PostgreSQL 18を使う必須回帰ゲート。"""

from contextlib import closing
import hashlib
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
from unittest.mock import patch
from uuid import uuid4
import xml.etree.ElementTree as ET

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL

from postgres_diagnostics import REQUIRED_TESTS, diagnostic_lines, execute_required_tests


ROOT = Path(__file__).resolve().parents[2]


class GateError(RuntimeError):
    """安全な診断メッセージのみ表示するゲートのエラー。"""


def require(condition, message):
    if not condition:
        raise GateError(message)


def safe_environment():
    # !NOTE: 既存DBや外部AIの設定を引き継がない。テストURLは後で生成する。
    names = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "LD_LIBRARY_PATH", "PYTHONUTF8")
    environment = {name: os.environ[name] for name in names if name in os.environ}
    environment.update(CALIBOO_AI_PROVIDER="manual", CALIBOO_DEMO_SEED="false",
                       CALIBOO_COOKIE_SECURE="false")
    return environment


def service():
    # !NOTE: 接続先は明示された postgres:18 CIサービスのループバックだけ。
    # 外部ホスト・既存DBへのURL指定を受け付けない。
    container = os.environ.get("CALIBOO_CI_POSTGRES_CONTAINER", "")
    port_value = os.environ.get("CALIBOO_CI_POSTGRES_PORT", "")
    password = os.environ.get("CALIBOO_CI_POSTGRES_PASSWORD", "")
    require(re.fullmatch(r"[0-9a-f]{12,64}", container), "CIサービスIDが必要です。")
    require(port_value.isascii() and port_value.isdigit(), "CIサービスのポートが必要です。")
    port = int(port_value)
    require(0 < port < 65536 and password, "CIサービス接続設定が必要です。")
    image = subprocess.check_output(
        ["docker", "inspect", "--format", "{{.Config.Image}}", container],
        text=True, timeout=20,
    ).strip()
    require(image == "postgres:18", "CIサービスのイメージは postgres:18 に限定します。")
    mapped = subprocess.check_output(
        ["docker", "port", container, "5432/tcp"], text=True, timeout=20,
    ).splitlines()
    require(any(line in {f"0.0.0.0:{port}", f"127.0.0.1:{port}"} for line in mapped),
            "CIサービスのマップされたポートと一致しません。")
    return container, port, password


def connection(port, password, database, username="postgres"):
    return psycopg.connect(
        host="127.0.0.1", port=port, user=username, password=password,
        dbname=database, connect_timeout=10, autocommit=True,
    )


def database_url(port, password, database, username):
    return URL.create(
        "postgresql+psycopg", username=username, password=password,
        host="127.0.0.1", port=port, database=database,
    ).render_as_string(hide_password=False)


def create_databases(port, password, names, owner, owner_password):
    with closing(connection(port, password, "postgres")) as conn:
        require(conn.info.server_version // 10000 == 18, "PostgreSQL 18 が必要です。")
        server_version = conn.execute("SHOW server_version").fetchone()[0]
        print(f"PostgreSQL: {server_version}; psycopg: {psycopg.__version__}", flush=True)
        # !NOTE: アプリと必須テストにはサービス管理者を使わない。
        conn.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}")
                     .format(sql.Identifier(owner), sql.Literal(owner_password)))
        for name in names:
            conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(name), sql.Identifier(owner),
            ))


def run_required_tests(environment, report):
    diagnostics = report.with_suffix(".diagnostics.json")
    returncode = execute_required_tests(ROOT / "backend", environment, report, diagnostics)
    # !NOTE: We never publish pytest stdout/stderr or JUnit failure contents.
    # Failed call/fixture metadata is generated separately without values or source text.
    lines = diagnostic_lines(diagnostics)
    for line in lines:
        print(line, flush=True)
    if report.is_file():
        cases = ET.parse(report).getroot().findall(".//testcase")
        failed = sum(case.find("failure") is not None for case in cases)
        errors = sum(case.find("error") is not None for case in cases)
        skipped = sum(case.find("skipped") is not None for case in cases)
        passed = len(cases) - failed - errors - skipped
        print(f"PostgreSQL pytest result: passed={passed} failed={failed} "
              f"errors={errors} skipped={skipped}", flush=True)
    else:
        cases = []
    if returncode != 0 and not lines:
        print("PostgreSQL pytest: no safe test diagnostic (collection/internal error or timeout)",
              flush=True)
    require(returncode == 0, f"PostgreSQL必須テスト失敗 (pytest exit={returncode})")
    require(len(cases) == len(REQUIRED_TESTS)
            and {case.get("name") for case in cases} == REQUIRED_TESTS,
            "PostgreSQL必須テストの件数・識別子が一致しません。")
    require(all(not list(case) for case in cases), "PostgreSQL必須テストに失敗またはskipがあります。")
    print(f"PostgreSQL候補必須回帰: {len(cases)} 件成功（skipなし）", flush=True)


def fingerprint(port, password, database):
    """バックアップ時点の全表内容・件数と採番状態を比較（内容は出力しない）。"""
    with closing(connection(port, password, database)) as conn:
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name"
        ).fetchall()
        require({name for name, in tables} >= {"users", "reports", "assignments"},
                "復元対象の業務テーブルがありません。")
        result = {}
        for name, in tables:
            rows = conn.execute(sql.SQL(
                'SELECT t::text FROM {}.{} AS t ORDER BY t::text COLLATE "C"'
            ).format(sql.Identifier("public"), sql.Identifier(name))).fetchall()
            digest = hashlib.sha256()
            for row, in rows:
                encoded = row.encode("utf-8")
                digest.update(len(encoded).to_bytes(8, "big"))
                digest.update(encoded)
            result[name] = (len(rows), digest.digest())
        sequences = {}
        names = conn.execute(
            "SELECT sequence_name FROM information_schema.sequences "
            "WHERE sequence_schema='public' ORDER BY sequence_name"
        ).fetchall()
        for name, in names:
            sequences[name] = conn.execute(sql.SQL(
                "SELECT last_value, is_called FROM {}.{}"
            ).format(sql.Identifier("public"), sql.Identifier(name))).fetchone()
        require(result["users"][0] > 0 and result["reports"][0] > 0 and sequences,
                "バックアップ対象に実行済みの合成業務記録がありません。")
        return result, sequences


def restore(container, port, password, source, target, owner, dump):
    # ソースは書込停止したテストDB。サービス同梱の18版クライアントを使う。
    before = fingerprint(port, password, source)
    with dump.open("xb") as output:
        subprocess.run(
            ["docker", "exec", container, "pg_dump", "--no-password", "--username=postgres",
             "--format=custom", "--no-owner", f"--dbname={source}"],
            stdout=output, check=True, timeout=120,
        )
    require(dump.stat().st_size > 0, "バックアップファイルが空です。")
    with dump.open("rb") as input_file:
        subprocess.run(
            ["docker", "exec", "-i", container, "pg_restore", "--no-password",
             "--username=postgres", "--exit-on-error", "--single-transaction",
             "--no-owner", f"--role={owner}", f"--dbname={target}"],
            stdin=input_file, check=True, timeout=120,
        )
    after = fingerprint(port, password, target)
    require(before == after, "復元前後の全表内容または採番状態が一致しません。")
    print(f"復元: {len(before[0])} 表・{len(before[1])} 採番シーケンスが一致", flush=True)


def verify_restored_api(environment, port, password, database, owner):
    """復元用DBを対象に通常の管理者作成・新人作成・日報登録・再起動を確認する。"""
    from fastapi.testclient import TestClient
    from pytest_socket import disable_socket

    restore_environment = dict(environment)
    restore_environment["CALIBOO_DATABASE_URL"] = database_url(port, password, database, owner)
    admin_password = secrets.token_urlsafe(24)
    member_password = secrets.token_urlsafe(24)
    disable_socket(allow_unix_socket=True)
    with patch.dict(os.environ, restore_environment, clear=True):
        from caliboo_api import manage
        from caliboo_api.main import app

        with closing(connection(port, password, database, owner)) as conn:
            max_user = conn.execute("SELECT max(id) FROM users").fetchone()[0]
        with (
            patch.object(sys, "argv", [
                "manage", "--login-id", "ci-restore-admin",
                "--display-name", "復元試験の合成管理者",
            ]),
            patch.object(manage.getpass, "getpass", return_value=admin_password),
        ):
            manage.main()
        with TestClient(app) as admin:
            login = admin.post("/api/auth/login", json={
                "loginId": "ci-restore-admin", "password": admin_password,
            })
            require(login.status_code == 200 and login.json()["role"] == "admin",
                    "復元後の管理者ログインに失敗しました。")
            result = admin.post("/api/users", json={
                "loginId": "ci-restore-member", "displayName": "復元試験の合成新人",
                "password": member_password, "role": "member",
            })
            require(result.status_code == 201, "復元後の新人作成に失敗しました。")
            require(result.json()["id"] > max_user, "復元後に採番が進みません。")
        report = "復元後の合成日報"
        with TestClient(app) as member:
            login = member.post("/api/auth/login", json={
                "loginId": "ci-restore-member", "password": member_password,
            })
            require(login.status_code == 200, "復元後の新人ログインに失敗しました。")
            result = member.post("/api/report", json={
                "date": "2026-11-26", "keep": report, "problem": "合成", "try": "合成",
                "mood": ["fun"], "status": "submitted",
            })
            require(result.status_code == 200, "復元後の日報提出に失敗しました。")
        with TestClient(app) as member:
            login = member.post("/api/auth/login", json={
                "loginId": "ci-restore-member", "password": member_password,
            })
            require(login.status_code == 200, "再起動後の新人ログインに失敗しました。")
            history = member.get("/api/report/history")
            require(history.status_code == 200
                    and any(row["keep"] == report for row in history.json()["history"]),
                    "再起動後の日報履歴が一致しません。")
    print("復元後の通常業務フローと再起動: 成功", flush=True)


def main():
    container, port, password = service()
    stamp = uuid4().hex[:12]
    migration = f"caliboo_issue25_migration_{stamp}"
    initialization = f"caliboo_issue25_init_{stamp}"
    restored = f"caliboo_issue25_restored_{stamp}"
    owner = f"caliboo_ci_{stamp}"
    owner_password = secrets.token_urlsafe(24)
    # 専用CIサービスはジョブ終了時に破棄される。既存DBを削除・上書きしない。
    create_databases(
        port, password, (migration, initialization, restored), owner, owner_password,
    )
    with tempfile.TemporaryDirectory(prefix="caliboo-postgres-") as temp:
        work = Path(temp)
        environment = safe_environment()
        environment.update(
            CALIBOO_TEST_POSTGRES_URL=database_url(port, owner_password, migration, owner),
            CALIBOO_TEST_POSTGRES_INIT_URL=database_url(
                port, owner_password, initialization, owner,
            ),
            CALIBOO_SQLITE_PATH=str(work / "test.db"),
        )
        run_required_tests(environment, work / "required.xml")
        restore(container, port, password, migration, restored, owner, work / "restore.dump")
        verify_restored_api(environment, port, owner_password, restored, owner)


if __name__ == "__main__":
    try:
        main()
    except GateError as error:
        print(f"PostgreSQLゲート失敗: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        # !NOTE: DB URL、認証値、バックアップの内容やSQLパラメータをログに出さない。
        print(f"PostgreSQLゲート失敗: {type(error).__name__}", file=sys.stderr)
        sys.exit(1)
