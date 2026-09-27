"""main.pyのlifespanを独立に検証する単体テスト。

!NOTE: `tests/unit/conftest.py`の`client`フィクスチャは、`TestClient(app)`のlifespan発火
       (`init_engine()`→`bootstrap_db()`)より前に、フィクスチャ自身が`init_engine()`→
       `bootstrap_db()`を呼んでしまっている。そのため、既存の`client`フィクスチャを使う
       テストだけでは`main.py`の`lifespan`内の初期化処理が壊れても検知できない。
       ここでは事前初期化を一切行わず、まっさらな一時DBパスを`CALIBOO_SQLITE_PATH`環境変数に
       セットしただけの状態で`with TestClient(app) as client:`に入り、lifespanだけで
       テーブル作成・シード投入(docs/architecture.md参照)が行われることを検証する。
"""

import os
import tempfile
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from caliboo_api.main import app


@pytest.fixture()
def fresh_sqlite_path() -> Iterator[str]:
    """`init_engine`/`bootstrap_db`を事前に呼ばず、環境変数のみ設定した一時DBパスを返す。"""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(db_path)

    previous_path = os.environ.get("CALIBOO_SQLITE_PATH")
    os.environ["CALIBOO_SQLITE_PATH"] = db_path
    try:
        yield db_path
    finally:
        if previous_path is None:
            os.environ.pop("CALIBOO_SQLITE_PATH", None)
        else:
            os.environ["CALIBOO_SQLITE_PATH"] = previous_path
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_lifespan_initializes_db_and_serves_home_summary(fresh_sqlite_path):
    with TestClient(app) as client:
        login_response = client.post(
            "/api/auth/login", json={"loginId": "yuki", "password": "caliboo-yuki"}
        )
        assert login_response.status_code == 200

        response = client.get("/api/home/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["name"] == "ユウキ"
    assert os.path.exists(fresh_sqlite_path)


def test_unauthenticated_request_returns_401_before_login(fresh_sqlite_path):
    """lifespan直後、未ログインで保護APIを呼ぶと401になる(認証がmain.pyで強制されている)。"""
    with TestClient(app) as client:
        response = client.get("/api/home/summary")

    assert response.status_code == 401
