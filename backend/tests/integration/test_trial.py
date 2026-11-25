"""限定試用の入口で通常のログイン・業務・終了・初期化を確認する。"""

from base64 import b64encode
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from caliboo_api.db import get_engine
from caliboo_api.trial import TrialSettings, create_trial_app

_ORIGIN = "https://trial.example.test"
_GATE = "sample-access-for-test-only-01"
_INSTRUCTOR = "sample-instructor-only-01"
_MEMBER = "sample-member-only-01"
_REPORT = {
    "date": "2026-11-25",
    "keep": "合成演習を完了しました",
    "problem": "合成演習の説明を見直します",
    "try": "合成例を追加します",
    "mood": ["happy"],
    "moodComment": "合成演習の感想",
    "status": "submitted",
}


@pytest.fixture
def trial_app(monkeypatch, tmp_path):
    for key in (
        "CALIBOO_TRIAL_TLS_CERTFILE", "CALIBOO_TRIAL_TLS_KEYFILE",
        "CALIBOO_SQLITE_PATH", "CALIBOO_DATABASE_URL",
        "CALIBOO_AI_MODEL", "OPENAI_API_KEY", "PORT",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "CALIBOO_TRIAL_ORIGIN": _ORIGIN,
        "CALIBOO_TRIAL_ACCESS_PASSWORD": _GATE,
        "CALIBOO_TRIAL_INSTRUCTOR_PASSWORD": _INSTRUCTOR,
        "CALIBOO_TRIAL_MEMBER_PASSWORD": _MEMBER,
        "CALIBOO_TRIAL_PROXY_IPS": "127.0.0.1/32",
        "CALIBOO_AI_PROVIDER": "manual",
        "CALIBOO_DEMO_SEED": "false",
        "CALIBOO_COOKIE_SECURE": "true",
    }.items():
        monkeypatch.setenv(key, value)
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        '<meta name="caliboo-trial" content="trial"><div id="root">試用fixture</div>',
        encoding="utf-8",
    )
    (dist / "assets" / "fixture.js").write_text("/* test */", encoding="utf-8")
    return create_trial_app(TrialSettings.from_env(), dist)


def _client(app, *, authenticated=True):
    headers = {"Origin": _ORIGIN}
    if authenticated:
        headers["Authorization"] = "Basic " + b64encode(
            f"trial:{_GATE}".encode("ascii"),
        ).decode("ascii")
    return TestClient(
        app,
        base_url=_ORIGIN,
        headers=headers,
        client=("127.0.0.1", 50000),
    )


def _login(client, login_id, password):
    response = client.post(
        "/api/auth/login", json={"loginId": login_id, "password": password},
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "secure" in cookie
    assert "httponly" in cookie
    return response.json()


def test_trial_entrypoint_workflow_and_reset(trial_app):
    with _client(trial_app, authenticated=False) as anonymous:
        health = anonymous.get("/healthz")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        assert anonymous.get("/").status_code == 401

        first_db = get_engine().url.database
        assert first_db is not None and Path(first_db).is_file()

        instructor = _client(trial_app)
        try:
            # The SPA and its content are served from the same origin as API requests.
            assert "試用fixture" in instructor.get("/").text
            assert "試用fixture" in instructor.get("/home").text
            assert instructor.get("/assets/fixture.js").text == "/* test */"
            assert instructor.get("/api/auth/me").status_code == 401
            role = _login(instructor, "trial-instructor", _INSTRUCTOR)["role"]
            assert role == "admin"
            listed = instructor.get("/api/users").json()["users"]
            assert sorted((user["loginId"], user["role"]) for user in listed) == [
                ("trial-instructor", "admin"), ("trial-member", "member"),
            ]
            assert instructor.get("/api/development/jobs").json()["provider"] == "manual"

            member = _client(trial_app)
            try:
                current = _login(member, "trial-member", _MEMBER)
                assert current["role"] == "member"
                assert member.get("/api/home/summary").status_code == 200
                assert member.get("/api/report/history").json()["history"] == []
                submitted = member.post("/api/report", json=_REPORT)
                assert submitted.status_code == 200
                assert submitted.json()["status"] == "submitted"
                jobs = instructor.get("/api/development/jobs").json()
                assert jobs["provider"] == "manual"
                assert any(job["kind"] == "strength" for job in jobs["jobs"])
                assert member.post("/api/auth/logout").status_code == 204
                assert member.get("/api/auth/me").status_code == 401
            finally:
                member.close()

            # A new login in the same trial instance sees submitted synthetic data.
            member = _client(trial_app)
            try:
                _login(member, "trial-member", _MEMBER)
                assert member.get("/api/report/history").json()["history"][0]["keep"] == (
                    _REPORT["keep"]
                )
                assert member.post("/api/auth/logout").status_code == 204
            finally:
                member.close()
            assert instructor.post("/api/auth/logout").status_code == 204
        finally:
            instructor.close()

    assert not Path(first_db).exists()

    # A later lifespan starts with a newly initialized DB and the same two roles.
    with _client(trial_app) as member:
        assert get_engine().url.database != first_db
        assert _login(member, "trial-member", _MEMBER)["role"] == "member"
        assert member.get("/api/report/history").json()["history"] == []
        assert member.post("/api/auth/logout").status_code == 204
