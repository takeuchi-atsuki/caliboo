"""認証まわりの内部実装(セッション行の掃除タイミング・ルート登録の完全性等)を
検証するテスト。公開HTTP APIの入出力自体は`test_auth_spec.py`を参照。"""

import caliboo_api.db as db
from caliboo_api.main import app
from caliboo_api.models import UserSession


def test_expired_sessions_are_cleaned_up_on_next_login(client, anonymous_client, expire_session):
    """期限切れセッションの掃除はログイン時に行う(`auth/session.py`の設計どおり)。"""
    token_hash = expire_session(client)

    login_response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "sora", "password": "caliboo-sora"}
    )
    assert login_response.status_code == 200

    with db.session_scope() as session:
        assert session.get(UserSession, token_hash) is None


def _iter_included_router_routes():
    """`include_router()`された各ルーターの実ルート(`_IncludedRouter.original_router
    .routes`)を辿り、`/api/`配下のルートを返す。

    !NOTE: このFastAPIバージョンは`include_router()`されたルーターを`_IncludedRouter`
           (遅延解決ラッパー)として`app.router.routes`に保持するため、素の`route.path`
           では中身が見えない。公開HTTP API定義の列挙(`test_auth_spec.py`)は
           `app.openapi()`で行うが、そこに現れない(=`include_in_schema=False`の)
           ルートが無いことを確認するには内部の`original_router`を辿る必要がある。
    """
    for route in app.router.routes:
        original_router = getattr(route, "original_router", None)
        if original_router is None:
            continue
        for sub_route in original_router.routes:
            path = getattr(sub_route, "path", None)
            if path is not None and path.startswith("/api/"):
                yield sub_route


def test_no_api_route_is_hidden_from_openapi_schema():
    """`/api/`配下に`include_in_schema=False`のルートが無いことを確認する。

    あると`app.openapi()`ベースの列挙(`test_auth_spec.py`)から漏れ、意図せず
    認証チェックの対象から外れてしまうため。
    """
    hidden_routes = [
        (route.path, sorted(route.methods))
        for route in _iter_included_router_routes()
        if not getattr(route, "include_in_schema", True)
    ]

    assert hidden_routes == []
