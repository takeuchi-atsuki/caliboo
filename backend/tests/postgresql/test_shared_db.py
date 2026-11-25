"""PostgreSQL 18の隔離DBを明示した場合だけ実行する業務回帰。

既存テストの一時SQLite fixtureは変更しない。ここでは使い捨ての空PG DBが必要。
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import os
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from caliboo_api import db, db_admin, manage
from caliboo_api.config import parse_database_url
from caliboo_api.data import assignment_proposal_data as proposal_data
from caliboo_api.main import app
from caliboo_api.migration import verify_migration
from caliboo_api.extension_models import QuizSuccess, UserProgress
from caliboo_api.models import AssignmentProposal, AssignmentSubmission, QuizQuestion, User


def isolated_url(name):
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not configured")
    url = parse_database_url(value)
    assert url.host in {"localhost", "127.0.0.1", "::1"} and url.port
    assert not url.query and url.database.startswith("caliboo_issue25_")
    engine = db.shared_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.dialect.server_version_info[0] == 18
            assert not inspect(connection).get_table_names(), "test requires a fresh empty database"
    finally:
        engine.dispose()
    return value, url


@pytest.fixture
def ephemeral_seed_passwords():
    """既存の業務シードを保ち、認証値だけをテストごとに独立生成する。"""
    passwords = {entry["login_id"]: secrets.token_urlsafe(24)
                 for entry in db.user_seed.USERS_SEED}
    rows = [dict(entry, password=passwords[entry["login_id"]])
            for entry in db.user_seed.USERS_SEED]
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(db.user_seed, "USERS_SEED", rows)
            yield passwords
    finally:
        # !NOTE: 平文はファイルや環境変数へ保存せず、fixture終了時に参照を破棄する。
        for row in rows:
            row.pop("password", None)
        passwords.clear()


def login(client, name, password):
    response = client.post("/api/auth/login",
                           json={"loginId": name, "password": password})
    assert response.status_code == 200


def prepare_sqlite_source(tmp_path, monkeypatch, passwords):
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "manual")
    monkeypatch.setenv("CALIBOO_DEMO_SEED", "true")
    monkeypatch.delenv("CALIBOO_DATABASE_URL", raising=False)
    sqlite = tmp_path / "source.db"
    monkeypatch.setenv("CALIBOO_SQLITE_PATH", str(sqlite))
    # 合成データを、ユーザーが利用するFastAPIからレコードとして作成する。
    with TestClient(app) as member:
        login(member, "yuki", passwords["yuki"])
        response = member.post("/api/report", json={
            "date": "2026-11-25", "keep": "移行前の合成記録", "problem": "", "try": "続ける",
            "mood": ["fun"], "status": "submitted",
        })
        assert response.status_code == 200
        before = member.get("/api/report/history").json()
    return sqlite, before


def create_initial_admin(monkeypatch):
    # 管理CLIの対話入力だけに渡す。環境変数やコマンド引数には設定しない。
    password = secrets.token_urlsafe(24)
    with monkeypatch.context() as patch:
        patch.setattr("sys.argv", [
            "manage", "--login-id", "test-admin", "--display-name", "合成管理者",
        ])
        patch.setattr(manage.getpass, "getpass", lambda prompt: password)
        manage.main()
    return password


def test_ephemeral_seed_credentials_on_sqlite(tmp_path, monkeypatch, ephemeral_seed_passwords):
    passwords = ephemeral_seed_passwords
    assert len(set(passwords.values())) == len(passwords)
    sqlite, before = prepare_sqlite_source(tmp_path, monkeypatch, passwords)
    assert sqlite.is_file()
    with TestClient(app) as client:
        for name in passwords:
            login(client, name, passwords[name])
        login(client, "yuki", passwords["yuki"])
        assert client.get("/api/report/history").json() == before


def test_ephemeral_initial_admin_credentials_on_sqlite(tmp_path, monkeypatch):
    monkeypatch.delenv("CALIBOO_DATABASE_URL", raising=False)
    monkeypatch.setenv("CALIBOO_SQLITE_PATH", str(tmp_path / "admin.db"))
    monkeypatch.setenv("CALIBOO_DEMO_SEED", "false")
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "manual")
    password = create_initial_admin(monkeypatch)
    with TestClient(app) as client:
        login(client, "test-admin", password)
        assert client.get("/api/users").status_code == 200


def test_migration_and_independent_sessions(tmp_path, monkeypatch, ephemeral_seed_passwords):
    value, url = isolated_url("CALIBOO_TEST_POSTGRES_URL")
    passwords = ephemeral_seed_passwords
    sqlite, before = prepare_sqlite_source(tmp_path, monkeypatch, passwords)
    snapshot = tmp_path / "snapshot.db"
    monkeypatch.setattr("sys.argv", ["db_admin", "snapshot", "--source", str(sqlite),
                                     "--output", str(snapshot)])
    db_admin.main()
    monkeypatch.setenv("CALIBOO_DATABASE_URL", value)
    monkeypatch.setattr("sys.argv", ["db_admin", "migrate", "--snapshot", str(snapshot)])
    db_admin.main()
    counts = verify_migration(snapshot, url)
    assert len(counts) == 40
    # 空DBに限る。2回目の実行では既存のレコードが残る。
    with pytest.raises(SystemExit):
        db_admin.main()
    assert verify_migration(snapshot, url) == counts

    with TestClient(app) as first:
        login(first, "yuki", passwords["yuki"])
        second = TestClient(app)
        try:
            login(second, "yuki", passwords["yuki"])
            assert first.cookies != second.cookies
            assert first.get("/api/report/history").json() == before
            assert second.get("/api/report/history").json() == before
            response = second.post("/api/report", json={
                "date": "2026-11-26", "keep": "移行後の合成記録", "problem": "", "try": "続ける",
                "status": "submitted",
            })
            assert response.status_code == 200
            assert first.get("/api/report/history").json()["history"][0]["keep"] == "移行後の合成記録"
            # 同一ユーザーが別々の問題に正解しても集計の書き落としがない。
            with db.session_scope() as session:
                user_id = session.query(User).filter_by(login_id="yuki").one().id
                questions = session.query(QuizQuestion).filter_by(category="technology").limit(
                    2).all()
                answers = [{"questionId": question.id, "selectedIndex": question.correct_index}
                           for question in questions]
            assert len(answers) == 2
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(client.post, "/api/quiz/answer", json=answer)
                           for client, answer in zip((first, second), answers)]
                assert all(future.result(timeout=30).status_code == 200 for future in futures)
            with db.session_scope() as session:
                correct = session.query(QuizSuccess).join(
                    QuizQuestion, QuizSuccess.question_id == QuizQuestion.id).filter(
                        QuizSuccess.user_id == user_id, QuizQuestion.category == "technology",
                    ).count()
                total = session.query(QuizQuestion).filter_by(category="technology").count()
                assert correct == 2
                assert session.get(UserProgress, (user_id, "technology")).percent == round(
                    correct * 100 / total)
        finally:
            second.close()
        other = TestClient(app)
        try:
            login(other, "sora", passwords["sora"])
            assert other.get("/api/report/history").json()["history"] == []
            assert other.get("/api/users").status_code == 403
        finally:
            other.close()

    # API再起動後の永続化、同時生成の冪等性(承認済みの課題案フロー)。
    with TestClient(app) as admin:
        another_admin = TestClient(app)
        login(admin, "sensei", passwords["sensei"])
        login(another_admin, "sensei", passwords["sensei"])
        with db.session_scope() as session:
            user_id = session.query(User).filter_by(login_id="sora").one().id
        # 両方の通常生成が既存案なしの判定を通ってから保存に進むよう、合成試験だけ同期する。
        ready = Barrier(2)
        generate = proposal_data._run_generator

        def synchronize_generation(session, target_user):
            output = generate(session, target_user)
            ready.wait(timeout=10)
            return output

        with monkeypatch.context() as patch:
            patch.setattr(proposal_data, "_run_generator", synchronize_generation)
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(client.post, "/api/assignment-proposals",
                                           json={"userId": user_id})
                           for client in (admin, another_admin)]
                responses = [future.result(timeout=30) for future in futures]
        # 応答本文を出さず、合成試験のHTTPステータス数値だけで失敗を切り分ける。
        proposal_status_codes = sorted(response.status_code for response in responses)
        assert proposal_status_codes == [200, 201], f"HTTP statuses: {proposal_status_codes}"
        assert responses[0].json()["id"] == responses[1].json()["id"]
        with db.session_scope() as session:
            pending = session.query(AssignmentProposal).filter(
                AssignmentProposal.target_user_id == user_id,
                AssignmentProposal.assignment_id.is_(None),
                AssignmentProposal.decided_at.is_(None),
            )
            assert pending.count() == 1
        another_admin.close()
        member = TestClient(app)
        login(member, "yuki", passwords["yuki"])
        assert member.get("/api/report/history").json()["history"][0]["keep"] == "移行後の合成記録"
        # 課題演習の通常フローの並行再提出・講師フィードバックを確認する。
        assignment = admin.post("/api/assignments", json={
            "title": "合成課題", "body": "合成課題本文",
        })
        assert assignment.status_code == 200
        assignment_id = assignment.json()["id"]
        submission_path = f"/api/assignments/{assignment_id}/submission"
        another_member = TestClient(app)
        login(another_member, "yuki", passwords["yuki"])
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(client.post, submission_path,
                                       json={"answerText": f"合成回答{index}"})
                       for index, client in enumerate((member, another_member))]
            assert all(future.result(timeout=30).status_code == 200 for future in futures)
        member_id = member.get("/api/auth/me").json()["id"]
        with db.session_scope() as session:
            assert session.query(AssignmentSubmission).filter_by(
                assignment_id=assignment_id, user_id=member_id).count() == 1
        feedback_path = f"/api/assignments/{assignment_id}/submissions/{member_id}/feedback"
        assert admin.post(feedback_path, json={"comment": "合成レビュー"}).status_code == 200
        assert another_member.get(f"/api/assignments/{assignment_id}").json()[
            "status"] == "reviewed"
        another_member.close()
        member.close()


def test_separate_first_initialization_without_demo(monkeypatch):
    value, _url = isolated_url("CALIBOO_TEST_POSTGRES_INIT_URL")
    monkeypatch.setenv("CALIBOO_DATABASE_URL", value)
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "manual")
    monkeypatch.setenv("CALIBOO_DEMO_SEED", "true")
    monkeypatch.setattr("sys.argv", ["db_admin", "init"])
    db_admin.main()
    with TestClient(app) as client:
        with db.session_scope() as session:
            assert session.query(User).count() == 0
        assert client.get("/api/home/summary").status_code == 401
    password = create_initial_admin(monkeypatch)
    with TestClient(app) as client:
        result = client.post("/api/auth/login", json={
            "loginId": "test-admin", "password": password,
        })
        assert result.status_code == 200 and result.json()["role"] == "admin"
        assert client.get("/api/users").status_code == 200
