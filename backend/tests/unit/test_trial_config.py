"""限定試用入口の設定を検証する。秘密値は合成fixtureのみ。"""

import pytest

from caliboo_api.trial import TrialSettings


@pytest.fixture
def trial_env(monkeypatch):
    for key in (
        "CALIBOO_TRIAL_TLS_CERTFILE", "CALIBOO_TRIAL_TLS_KEYFILE",
        "CALIBOO_SQLITE_PATH", "CALIBOO_DATABASE_URL",
        "CALIBOO_AI_MODEL", "OPENAI_API_KEY", "PORT",
    ):
        monkeypatch.delenv(key, raising=False)
    values = {
        "CALIBOO_TRIAL_ORIGIN": "https://trial.example.test",
        "CALIBOO_TRIAL_ACCESS_PASSWORD": "sample-access-for-test-only-01",
        "CALIBOO_TRIAL_INSTRUCTOR_PASSWORD": "sample-instructor-only-01",
        "CALIBOO_TRIAL_MEMBER_PASSWORD": "sample-member-only-01",
        "CALIBOO_TRIAL_PROXY_IPS": "127.0.0.1/32",
        "CALIBOO_AI_PROVIDER": "manual",
        "CALIBOO_DEMO_SEED": "false",
        "CALIBOO_COOKIE_SECURE": "true",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return values


def test_explicit_trial_configuration(trial_env):
    assert TrialSettings.from_env() is not None


@pytest.mark.parametrize("key", [
    "CALIBOO_TRIAL_ORIGIN", "CALIBOO_TRIAL_ACCESS_PASSWORD",
    "CALIBOO_TRIAL_INSTRUCTOR_PASSWORD", "CALIBOO_TRIAL_MEMBER_PASSWORD",
    "CALIBOO_TRIAL_PROXY_IPS", "CALIBOO_AI_PROVIDER",
    "CALIBOO_DEMO_SEED", "CALIBOO_COOKIE_SECURE",
])
def test_required_trial_setting(trial_env, monkeypatch, key):
    monkeypatch.delenv(key)
    with pytest.raises(ValueError):
        TrialSettings.from_env()


@pytest.mark.parametrize("key,value", [
    ("CALIBOO_TRIAL_ORIGIN", "http://trial.example.test"),
    ("CALIBOO_TRIAL_ACCESS_PASSWORD", "short"),
    ("CALIBOO_TRIAL_INSTRUCTOR_PASSWORD", "short"),
    ("CALIBOO_TRIAL_MEMBER_PASSWORD", "short"),
    ("CALIBOO_TRIAL_MEMBER_PASSWORD", "sample-instructor-only-01"),
    ("CALIBOO_AI_PROVIDER", "openai"),
    ("CALIBOO_DEMO_SEED", "true"),
    ("CALIBOO_COOKIE_SECURE", "false"),
    ("CALIBOO_SQLITE_PATH", "/tmp/unused-synthetic-test.sqlite"),
    ("CALIBOO_DATABASE_URL", "postgresql://invalid.example.test/synthetic"),
    ("CALIBOO_AI_MODEL", "synthetic-test-model"),
    ("OPENAI_API_KEY", "sample-not-an-api-key"),
    ("PORT", "not-a-port"),
    ("PORT", "65536"),
    ("CALIBOO_TRIAL_ORIGIN", "https://trial.example.test/"),
])
def test_trial_configuration_rejects_incompatible_values(trial_env, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        TrialSettings.from_env()


def test_direct_tls_configuration(trial_env, monkeypatch, tmp_path):
    # Unit-level: TLS file selection only (the actual TLS handshake is exercised by trial_smoke).
    cert, key = tmp_path / "example-cert.pem", tmp_path / "example-key.pem"
    cert.touch()
    key.touch()
    monkeypatch.delenv("CALIBOO_TRIAL_PROXY_IPS")
    monkeypatch.setenv("CALIBOO_TRIAL_TLS_CERTFILE", str(cert))
    monkeypatch.setenv("CALIBOO_TRIAL_TLS_KEYFILE", str(key))
    monkeypatch.setenv("CALIBOO_TRIAL_ORIGIN", "https://127.0.0.1:14443")
    monkeypatch.setenv("PORT", "14443")
    settings = TrialSettings.from_env()
    assert settings.proxy_ips == ()
    assert settings.tls_certfile == cert
    assert settings.tls_keyfile == key
    assert settings.port == 14443


def test_trial_build_required(trial_env, tmp_path):
    from caliboo_api.trial import create_trial_app

    with pytest.raises(ValueError, match="frontend"):
        create_trial_app(TrialSettings.from_env(), tmp_path)

    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    with pytest.raises(ValueError, match="frontend"):
        create_trial_app(TrialSettings.from_env(), tmp_path)


def test_startup_refuses_missing_required_settings(trial_env, monkeypatch):
    from caliboo_api.trial import main

    monkeypatch.delenv("CALIBOO_TRIAL_ORIGIN")
    with pytest.raises(SystemExit, match="startup refused"):
        main()


def test_proxy_ip_list_configuration(trial_env, monkeypatch):
    monkeypatch.setenv("CALIBOO_TRIAL_PROXY_IPS", "127.0.0.1/32, ::1")
    assert TrialSettings.from_env().proxy_ips == ("127.0.0.1/32", "::1")


@pytest.fixture
def trial_build(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        '<meta name="caliboo-trial" content="trial">試用fixture',
        encoding="utf-8",
    )
    (tmp_path / "assets" / "fixture.js").write_text("/* test */", encoding="utf-8")
    return tmp_path


def test_trial_readiness_and_frontend_assembly(trial_env, trial_build):
    from base64 import b64encode
    from fastapi.testclient import TestClient
    from caliboo_api.trial import create_trial_app

    settings = TrialSettings.from_env()
    app = create_trial_app(settings, trial_build)
    with_no_lifespan = TestClient(app, base_url=settings.origin)
    try:
        assert with_no_lifespan.get("/healthz").status_code == 503
        assert with_no_lifespan.get("/").status_code == 401
    finally:
        with_no_lifespan.close()

    auth = "Basic " + b64encode(f"trial:{settings.access_password}".encode("ascii")).decode("ascii")
    with TestClient(app, base_url=settings.origin, headers={"Authorization": auth}) as client:
        response = client.get("/healthz")
        assert response.json() == {"status": "ok"}
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
        assert client.get("/").text.endswith("試用fixture")
        assert client.get("/login").text.endswith("試用fixture")
        assert client.get("/assignments/12").status_code == 200
        assert client.get("/assets/fixture.js").text == "/* test */"
        assert client.get("/not-a-page").status_code == 404
    assert not app.state.trial_ready


@pytest.mark.parametrize("mode", ["proxy", "direct"])
def test_entrypoint_dispatches_selected_tls_mode(trial_env, monkeypatch, tmp_path, mode):
    from caliboo_api import trial

    if mode == "direct":
        cert, key = tmp_path / "example-cert.pem", tmp_path / "example-key.pem"
        cert.touch()
        key.touch()
        monkeypatch.delenv("CALIBOO_TRIAL_PROXY_IPS")
        monkeypatch.setenv("CALIBOO_TRIAL_TLS_CERTFILE", str(cert))
        monkeypatch.setenv("CALIBOO_TRIAL_TLS_KEYFILE", str(key))
        monkeypatch.setenv("CALIBOO_TRIAL_ORIGIN", "https://127.0.0.1:14443")
        monkeypatch.setenv("PORT", "14443")
    served = object()
    invocation = {}

    def create_app(settings, dist_dir):
        invocation["settings"] = settings
        assert dist_dir.parts[-2:] == ("frontend", "dist")
        return served

    def run(app, **kwargs):
        invocation.update(kwargs)
        assert app is served

    monkeypatch.setattr(trial, "create_trial_app", create_app)
    monkeypatch.setattr(trial.uvicorn, "run", run)
    trial.main()
    assert invocation["host"] == ("0.0.0.0" if mode == "proxy" else "127.0.0.1")
    assert invocation["workers"] == 1
    assert invocation["reload"] is False
    assert invocation["access_log"] is False
    assert invocation["proxy_headers"] == (mode == "proxy")
    if mode == "direct":
        assert invocation["ssl_certfile"] == str(cert)
        assert invocation["ssl_keyfile"] == str(key)
        assert invocation["port"] == 14443
    else:
        assert invocation["forwarded_allow_ips"] == ["127.0.0.1/32"]
        assert invocation["port"] == 10000


def test_choose_only_one_tls_mode(trial_env, monkeypatch, tmp_path):
    cert = tmp_path / "example-cert.pem"
    cert.touch()
    monkeypatch.setenv("CALIBOO_TRIAL_TLS_CERTFILE", str(cert))
    with pytest.raises(ValueError, match="either"):
        TrialSettings.from_env()


def test_entrypoint_reports_unreadable_build(trial_env, monkeypatch):
    from caliboo_api import trial

    def create_app(_settings, _dist_dir):
        raise OSError("test fixture cannot be read")

    monkeypatch.setattr(trial, "create_trial_app", create_app)
    with pytest.raises(SystemExit, match="configuration or build unavailable"):
        trial.main()
