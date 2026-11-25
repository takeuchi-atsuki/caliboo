#!/usr/bin/env python3
"""#26: 同じ合成データで、通常の画面取得APIを改修前後に比較する。"""

import argparse
import hashlib
import json
import math
import os
import socket
import statistics
import tempfile
import time
from collections import defaultdict
from contextlib import ExitStack
from contextvars import ContextVar
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine

# !NOTE: 実運用のDBパスやAI設定を引き継がない。DBは実行ごとの一時領域に限定する。
# #25導入後も、起動環境から引き継いだDB接続先を使用しない。
os.environ.pop("CALIBOO_DATABASE_URL", None)
os.environ.pop("CALIBOO_SQLITE_PATH", None)
os.environ["CALIBOO_AI_PROVIDER"] = "manual"
os.environ["CALIBOO_DEMO_SEED"] = "false"
os.environ["CALIBOO_COOKIE_SECURE"] = "false"

from caliboo_api import db  # noqa: E402
from caliboo_api.auth.password import hash_password  # noqa: E402
from caliboo_api.data.account_data import initialize_profile  # noqa: E402
from caliboo_api.extension_models import (  # noqa: E402
    AccountState, AgentJob, AgentJobExecution, LearningAction,
    StrengthCandidate, StrengthInterpretation,
)
from caliboo_api.main import app  # noqa: E402
from caliboo_api.models import (  # noqa: E402
    Assignment, AssignmentRecipient, AssignmentSubmission, Report, User,
)

PASSWORD = "local-synthetic-fixture-only"
MEMBERS = 24
ROUNDS = 2
FIXTURES = {
    "small": dict(reports=3, jobs=2, common_assignments=6, personal_assignments=2),
    "populated": dict(reports=24, jobs=10, common_assignments=36, personal_assignments=12),
}
SKILLS = ("DBAD", "DTAN", "PROG", "DOCM", "TEST", "RLMT")
STAMP = "2026-01-01T09:00:00+00:00"

# SQLカウンタはリクエスト単位。スレッド間で同じカウンタを参照する。
current_measurement = ContextVar("current_measurement", default=None)


def count_sql(conn, cursor, statement, parameters, context, executemany):
    counter = current_measurement.get()
    if counter is not None:
        counter[0] += 1


@app.middleware("http")
async def measure_request(request, call_next):
    counter = [0]
    token = current_measurement.set(counter)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Benchmark-Queries"] = str(counter[0])
        response.headers["X-Benchmark-Server-Ms"] = str(
            (time.perf_counter() - start) * 1000
        )
        return response
    finally:
        current_measurement.reset(token)


def block_network(original):
    """TestClient内のUNIXソケット以外に接続しない。"""
    def guarded(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise OSError("TCP/IP network disabled for synthetic benchmark")
        return original(self, address)

    return guarded


def create_assignment(session, index, user_id=None):
    row = Assignment(
        title=f"計測用課題-{index:03d}", body="合成の学習課題です。" * 20,
        created_at=STAMP,
    )
    session.add(row)
    session.flush()
    if user_id is not None:
        session.add(AssignmentRecipient(assignment_id=row.id, user_id=user_id))
    return row.id


def seed_member(session, user_id, admin_id, fixture):
    reports = []
    for index in range(fixture["reports"]):
        day = (date(2026, 1, 1) + timedelta(days=index)).isoformat()
        row = Report(
            user_id=user_id, date=day, keep="手順を整理して確認した。",
            problem="説明の順番に迷った。", try_="確認項目を整理する。",
            mood=None, mood_comment="", status="submitted",
            saved_at=f"{day}T09:00:00+00:00",
        )
        session.add(row)
        reports.append(row)
    session.flush()

    # 完了済みジョブと候補の履歴、未処理ジョブ1件を作る。
    # 最新の各スキルのみ承認済み。他は保留中・過去に置き換えられた候補。
    latest = {}
    for index in range(fixture["jobs"]):
        report = reports[index % len(reports)]
        material = {
            "id": f"report:{report.id}:keep", "text": report.keep,
            "date": report.date, "kind": "report", "field": "keep",
            "evidenceEligible": True, "sourceRole": "self_report",
        }
        pending = index == fixture["jobs"] - 1
        row = AgentJob(
            user_id=user_id, kind="strength",
            fingerprint=f"synthetic-{user_id}-{index}",
            materials={"schemaVersion": "strength-materials.v1", "sources": [material]},
            status="pending" if pending else "completed",
            created_at=STAMP, completed_at=None if pending else STAMP,
        )
        session.add(row)
        session.flush()
        if index % 3 != 0:
            session.add(AgentJobExecution(job_id=row.id, attempts=1))
        if pending:
            continue

        code = SKILLS[index % len(SKILLS)]
        status = "approved" if index % 3 != 2 else "pending"
        if status == "approved" and code in latest:
            latest[code].status = "superseded"
        candidate = StrengthCandidate(
            user_id=user_id, job_id=row.id, label=f"合成強み-{code}-{index}",
            skill_code=code, confidence=70,
            evidence=[{"materialId": material["id"], "quote": material["text"],
                       "source": material}],
            growth_action="確認した項目を振り返る。", status=status,
            decided_by=admin_id if status == "approved" else None,
            decided_at=STAMP if status == "approved" else None,
        )
        row.result = {
            "trace": {"provider": "codex_agent", "model": "synthetic",
                      "promptVersion": "synthetic"},
            "candidates": [{
                "label": candidate.label, "skillCode": code, "confidence": 70,
                "evidence": [{"materialId": material["id"], "quote": material["text"]}],
                "growthAction": candidate.growth_action,
            }],
            "notes": "合成の解析結果",
        }
        session.add(candidate)
        session.flush()
        if status == "approved":
            latest[code] = candidate
        if index % 3 != 0:
            session.add(StrengthInterpretation(
                candidate_id=candidate.id, kind="ability",
                summary="作業順を整理できる。", scope_note="合成資料内での所見。",
            ))

    for candidate in latest.values():
        session.add(LearningAction(
            user_id=user_id, candidate_id=candidate.id,
            strength_snapshot={"label": candidate.label, "growthAction": candidate.growth_action},
            title="学習手順を整理する", success_criteria="確認項目を記録する",
            created_at=STAMP, updated_at=STAMP,
        ))


def seed_fixture(fixture):
    """25人の架空アカウントを作成し、通常の画面表示に必要な行だけを用意する。"""
    users = []
    with db.session_scope() as session:
        for index in range(MEMBERS + 1):
            user = User(
                login_id=f"synthetic-{index:02d}", display_name=f"計測用利用者-{index:02d}",
                role="admin" if index == 0 else "member",
                password_hash=hash_password(PASSWORD), created_at=STAMP,
            )
            session.add(user)
            session.flush()
            initialize_profile(session, user.id)
            session.add(AccountState(user_id=user.id, active=True))
            users.append((user.id, user.login_id))
        common = [
            create_assignment(session, index)
            for index in range(fixture["common_assignments"])
        ]
        for index, (user_id, _) in enumerate(users[1:], 1):
            personal = [
                create_assignment(session, index * 100 + offset, user_id)
                for offset in range(fixture["personal_assignments"])
            ]
            for offset, assignment_id in enumerate(common + personal):
                if offset % 3 == 0:
                    continue
                reviewed = offset % 3 == 1
                session.add(AssignmentSubmission(
                    assignment_id=assignment_id, user_id=user_id,
                    answer_text="合成の提出内容", submitted_at=STAMP,
                    feedback_comment="合成の講師コメント" if reviewed else None,
                    feedback_at=STAMP if reviewed else None,
                ))
            seed_member(session, user_id, users[0][0], fixture)
        session.commit()
        totals = {
            model.__tablename__: session.query(model).count()
            for model in (User, Report, Assignment, AssignmentRecipient, AssignmentSubmission,
                          AgentJob, AgentJobExecution, StrengthCandidate,
                          StrengthInterpretation, LearningAction)
        }
    return users, totals


def fetch(client, path):
    start = time.perf_counter()
    response = client.get(path)
    elapsed = (time.perf_counter() - start) * 1000
    response.raise_for_status()
    return {
        "client_ms": round(elapsed, 3),
        "server_ms": round(float(response.headers["X-Benchmark-Server-Ms"]), 3),
        "sql": int(response.headers["X-Benchmark-Queries"]),
        "status": response.status_code,
    }, response.json()


def describe(samples):
    values = sorted(samples)
    return {
        "min": min(values), "max": max(values),
        "p50": round(statistics.median(values), 3),
        "p95": round(values[math.ceil(len(values) * 0.95) - 1], 3),
    }


def summarize(samples, responses):
    return {
        label: {
            "samples": len(rows),
            "client_ms": describe([row["client_ms"] for row in rows]),
            "server_ms": describe([row["server_ms"] for row in rows]),
            "sql": describe([row["sql"] for row in rows]),
            "non_200": sum(row["status"] != 200 for row in rows),
            "response_sha256": hashlib.sha256(
                json.dumps(responses[label], sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
        }
        for label, rows in samples.items()
    }


def run_profile(name):
    fixture = FIXTURES[name]
    samples = defaultdict(list)
    responses = defaultdict(list)
    with tempfile.TemporaryDirectory(prefix="caliboo-26-synthetic-") as temp_dir:
        os.environ["CALIBOO_SQLITE_PATH"] = str(Path(temp_dir) / "fixture.db")
        with TestClient(app, base_url="http://testserver"), ExitStack() as stack:
            # lifespanは一度だけ起動し、利用者ごとにCookie jarを分ける。
            users, totals = seed_fixture(fixture)
            clients = []
            for user_id, login_id in users:
                client = TestClient(app, base_url="http://testserver")
                stack.callback(client.close)
                response = client.post("/api/auth/login", json={
                    "loginId": login_id, "password": PASSWORD,
                })
                response.raise_for_status()
                assert response.json()["id"] == user_id
                clients.append(client)

            member_paths = (
                ("home", "/api/home/summary"),
                ("strengths", "/api/development/strengths"),
                ("actions", "/api/development/actions"),
                ("assignments", "/api/assignments"),
            )
            admin = clients[0]
            # ウォームアップ(測定に含めない)。
            for label, path in member_paths:
                fetch(clients[1], path)
            fetch(admin, "/api/development/jobs")
            fetch(admin, f"/api/development/strengths?userId={users[1][0]}")

            def visit(client, label, path):
                record, body = fetch(client, path)
                samples[label].append(record)
                responses[label].append(body)
                return body

            # 同時接続や最大負荷ではなく、各利用者が順番にホーム・強み・課題を閲覧。
            # 操作の間隔を空ける。この測定にはログイン・描画・5秒ポーリング待ちは含まない。
            for _round in range(ROUNDS):
                for index, client in enumerate(clients[1:], 1):
                    for label, path in member_paths:
                        body = visit(client, label, path)
                        if label == "assignments":
                            assert len(body["assignments"]) == (
                                fixture["common_assignments"] + fixture["personal_assignments"]
                            )
                            assert all(
                                item["target"] is None or item["target"]["id"] == users[index][0]
                                for item in body["assignments"]
                            )
                        time.sleep(0.15)
                visit(admin, "admin_jobs", "/api/development/jobs")
                for user_id, _ in users[1:]:
                    visit(admin, "admin_strengths", f"/api/development/strengths?userId={user_id}")
                    time.sleep(0.15)
        # Windows等でも一時DBの削除を妨げないようにする。
        db._engine.dispose()
    return {
        "fixture": name, "users": MEMBERS + 1, "member_count": MEMBERS,
        "rounds": ROUNDS, "table_rows": totals,
        "visible_assignments_per_member": (
            fixture["common_assignments"] + fixture["personal_assignments"]
        ),
        "endpoints": summarize(samples, responses),
    }


def prepare_fixture(name):
    # ブラウザで通常操作を行う場合にも同一データを使えるよう、
    # 既存DBを受け取らず新規の一時ディレクトリにだけ作成する。
    temp_dir = Path(tempfile.mkdtemp(prefix="caliboo-26-gui-synthetic-"))
    db_path = str(temp_dir / "fixture.db")
    os.environ["CALIBOO_SQLITE_PATH"] = db_path
    db.init_engine(db_path)
    db.bootstrap_db()
    try:
        users, totals = seed_fixture(FIXTURES[name])
    finally:
        db._engine.dispose()
    return {
        "fixture": name, "sqlite_path": db_path, "table_rows": totals,
        "login_ids": [login_id for _, login_id in users],
        "notice": "実運用と分離したローカルGUI用の一時DB。終了後にこの一時領域を破棄する。",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("small", "populated", "both"), default="both")
    parser.add_argument("--prepare-fixture", action="store_true",
                        help="逐次API計測はせず、手動GUI計測用の一時DBを新規作成する")
    args = parser.parse_args()
    if args.prepare_fixture and args.profile == "both":
        parser.error("--prepare-fixture requires --profile small or populated")
    profiles = list(FIXTURES) if args.profile == "both" else [args.profile]
    event.listen(Engine, "before_cursor_execute", count_sql)
    try:
        with patch.object(socket.socket, "connect", block_network(socket.socket.connect)), \
                patch.object(socket.socket, "connect_ex", block_network(socket.socket.connect_ex)):
            if args.prepare_fixture:
                result = prepare_fixture(args.profile)
            else:
                result = {"results": [run_profile(name) for name in profiles]}
    finally:
        event.remove(Engine, "before_cursor_execute", count_sql)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
