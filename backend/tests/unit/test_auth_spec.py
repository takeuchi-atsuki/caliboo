"""認証API(`POST /api/auth/login`・`POST /api/auth/logout`・`GET /api/auth/me`)の
公開HTTP APIとしての入出力(仕様)テスト。"""

import re

import pytest

import caliboo_api.db as db
from caliboo_api.main import app
from caliboo_api.models import User

# --- login ---


def test_login_success_returns_current_user_and_sets_cookie(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "yuki", "password": "caliboo-yuki"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["loginId"] == "yuki"
    assert body["displayName"] == "ユウキ"
    assert body["role"] == "member"
    assert isinstance(body["id"], int)
    assert "caliboo_session" in response.cookies


def test_login_admin_success(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "sensei", "password": "caliboo-sensei"}
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_login_wrong_login_id_returns_401(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "no-such-user", "password": "caliboo-yuki"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid login id or password"}


def test_login_wrong_password_returns_same_401(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "yuki", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid login id or password"}


def test_login_blank_login_id_returns_422(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/login", json={"loginId": " ", "password": "caliboo-yuki"}
    )

    assert response.status_code == 422


def test_login_blank_password_returns_422(anonymous_client):
    response = anonymous_client.post("/api/auth/login", json={"loginId": "yuki", "password": ""})

    assert response.status_code == 422


@pytest.mark.parametrize("password", [" caliboo-yuki", "caliboo-yuki ", " caliboo-yuki "])
def test_login_password_with_surrounding_whitespace_is_not_stripped(anonymous_client, password):
    """passwordは前後空白をstripしない(loginIdと異なりNonEmptyTextを使わない)ため、
    正しいパスワードに空白を付けただけでも別の値として扱われ401になる。"""
    response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "yuki", "password": password}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid login id or password"}


def test_login_with_null_password_hash_returns_401(anonymous_client):
    """`password_hash`が`None`のユーザー(SSO移行後等でパスワード未設定)でログインしても、
    500ではなくダミーハッシュ検証を経て401になる。"""
    with db.session_scope() as session:
        user = session.query(User).filter(User.login_id == "yuki").first()
        user.password_hash = None
        session.commit()

    response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "yuki", "password": "caliboo-yuki"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid login id or password"}


# --- me ---


def test_me_returns_current_user(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["loginId"] == "yuki"
    assert body["role"] == "member"


def test_me_without_login_returns_401(anonymous_client):
    response = anonymous_client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "not authenticated"}


# --- logout ---


def test_logout_then_me_returns_401(client):
    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204
    assert logout_response.content == b""

    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_logout_without_cookie_is_idempotent(anonymous_client):
    response = anonymous_client.post("/api/auth/logout")

    assert response.status_code == 204


def test_logout_with_unknown_cookie_is_idempotent(anonymous_client):
    anonymous_client.cookies.set("caliboo_session", "not-a-real-token")

    response = anonymous_client.post("/api/auth/logout")

    assert response.status_code == 204


def test_logout_invalidates_server_side_session(client):
    """ログアウト前のトークンをCookieへ戻して呼び直しても、サーバー側のセッションは
    破棄済みなので保護APIは401になる(Cookie削除だけの見せかけのログアウトでないこと)。"""
    token_before_logout = client.cookies.get("caliboo_session")

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    client.cookies.set("caliboo_session", token_before_logout)
    response = client.get("/api/auth/me")

    assert response.status_code == 401


# --- セッションCookieの属性 ---

def _session_cookie_header(response) -> str:
    all_cookies = response.headers.get_list("set-cookie")
    headers = [h for h in all_cookies if h.startswith("caliboo_session=")]
    assert len(headers) == 1
    return headers[0]


def test_login_sets_cookie_with_expected_attributes(anonymous_client):
    response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "yuki", "password": "caliboo-yuki"}
    )

    header = _session_cookie_header(response)
    assert "HttpOnly" in header
    assert "SameSite=lax" in header.lower() or "samesite=lax" in header.lower()
    assert "Path=/" in header
    assert "Max-Age=43200" in header
    assert "Secure" not in header


def test_login_sets_secure_cookie_when_cookie_secure_enabled(anonymous_client, monkeypatch):
    monkeypatch.setenv("CALIBOO_COOKIE_SECURE", "1")

    response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "yuki", "password": "caliboo-yuki"}
    )

    header = _session_cookie_header(response)
    assert "Secure" in header


def test_logout_deletes_cookie(client):
    response = client.post("/api/auth/logout")

    header = _session_cookie_header(response)
    assert "Max-Age=0" in header or "1970" in header


# --- セッション期限(12時間) ---


def test_expired_session_returns_401_and_logout_still_succeeds(client, expire_session):
    expire_session(client)

    response = client.get("/api/home/summary")
    assert response.status_code == 401
    assert response.json() == {"detail": "not authenticated"}

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204


# --- 全/api/*ルートの認証必須(login/logout以外) ---

_EXEMPT_PATHS = {"/api/auth/login", "/api/auth/logout"}
_DUMMY_PATH_PARAMS = {
    "action_id": "1",
    "job_id": "1", "candidate_id": "1", "thread_id": "1",
    "assignment_id": "1",
    "proposal_id": "1",
    "user_id": "1",
    "report_id": "1",
    "dept_id": "dev",
    "run_id": "run_0001",
}
_PATH_PARAM_PATTERN = re.compile(r"\{([^}]+)\}")


def _fill_path_params(path: str) -> str:
    return _PATH_PARAM_PATTERN.sub(lambda match: _DUMMY_PATH_PARAMS[match.group(1)], path)


def _iter_api_routes():
    """公開HTTP API定義(`app.openapi()["paths"]`)から`/api/`配下のMethod・Pathの組を返す。

    !NOTE: `app.routes`(FastAPI内部のルーティングテーブル)ではなく`app.openapi()`を使う。
           `app.routes`はこのFastAPIバージョンでは`include_router()`されたルーターを
           `_IncludedRouter`(遅延解決ラッパー)として保持し、内部実装に依存した辿り方が
           必要になってしまう。`app.openapi()`は公開されるHTTP API定義そのものであり、
           内部実装に依存せずMethod・Pathを列挙できる。
    """
    paths = app.openapi()["paths"]
    for path, methods_by_verb in paths.items():
        if not path.startswith("/api/"):
            continue
        for method in methods_by_verb:
            if method.upper() == "HEAD":
                continue
            yield method.upper(), path


_ROUTES_REQUIRING_AUTH = sorted(
    (method, path) for method, path in _iter_api_routes() if path not in _EXEMPT_PATHS
)


def test_at_least_one_route_is_collected_per_router():
    """列挙ロジック自体が壊れて0件を拾っていないことを保証する(誤って全てpassしないため)。"""
    assert len(_ROUTES_REQUIRING_AUTH) >= 20


@pytest.mark.parametrize("method,path", _ROUTES_REQUIRING_AUTH)
def test_unauthenticated_request_to_protected_route_returns_401(anonymous_client, method, path):
    resolved_path = _fill_path_params(path)

    response = anonymous_client.request(method, resolved_path)

    assert response.status_code == 401
    assert response.json() == {"detail": "not authenticated"}


def test_login_and_logout_paths_are_exempted_from_authentication():
    all_paths = {path for _, path in _iter_api_routes()}
    assert _EXEMPT_PATHS <= all_paths
