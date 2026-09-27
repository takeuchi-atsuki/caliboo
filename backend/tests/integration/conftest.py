import os
import tempfile
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import caliboo_api.db as db
from caliboo_api.db import bootstrap_db, init_engine
from caliboo_api.main import app
from caliboo_api.models import User

_SEED_PASSWORDS = {
    "yuki": "caliboo-yuki",
    "sora": "caliboo-sora",
    "haruka": "caliboo-haruka",
    "sensei": "caliboo-sensei",
}


@pytest.fixture()
def bootstrapped_db() -> Iterator[str]:
    """FastAPIアプリを介さず、DB層(db.py/models.py/data/*.py)単体をテストするための
    初期化済み一時SQLiteファイルを提供する。
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(db_path)

    init_engine(db_path)
    bootstrap_db()
    try:
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture()
def user_ids(bootstrapped_db: str) -> dict[str, int]:
    """データ層(`data/*.py`)を直接呼ぶテストが、シード済みユーザーの
    `login_id → id`を引けるようにする。"""
    with db.session_scope() as session:
        return {user.login_id: user.id for user in session.query(User).all()}


@pytest.fixture()
def app_client() -> Iterator[TestClient]:
    """1つの一時SQLiteファイル・1回のlifespanを、複数のTestClientで共有するための土台。

    !NOTE: `CALIBOO_SQLITE_PATH`環境変数も合わせて設定するのは、`with TestClient(app)`が
           発火させるアプリのlifespan内でも`init_engine()`が呼ばれるため(`main.py`参照)。
           ログインIDごとにCookie jarを分けた複数クライアント(`client`/`admin_client`/
           `other_member_client`/`anonymous_client`)が必要なため、この`with`ブロックの
           中でだけ追加の`TestClient(app)`(`with`無し)を作る(`login_as`参照)。
           `with TestClient(app)`を複数回使うとlifespanが複数回発火し、一時DBを
           複数回bootstrapしようとして共有できなくなる。
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(db_path)

    previous_path = os.environ.get("CALIBOO_SQLITE_PATH")
    os.environ["CALIBOO_SQLITE_PATH"] = db_path
    try:
        init_engine(db_path)
        bootstrap_db()

        with TestClient(app) as test_client:
            yield test_client
    finally:
        if previous_path is None:
            os.environ.pop("CALIBOO_SQLITE_PATH", None)
        else:
            os.environ["CALIBOO_SQLITE_PATH"] = previous_path
        if os.path.exists(db_path):
            os.unlink(db_path)


def _login(login_id: str) -> TestClient:
    test_client = TestClient(app)
    response = test_client.post(
        "/api/auth/login",
        json={"loginId": login_id, "password": _SEED_PASSWORDS[login_id]},
    )
    assert response.status_code == 200
    return test_client


@pytest.fixture()
def login_as(app_client: TestClient):
    """`app_client`と同じengineを共有する、専用Cookie jarを持つ新規クライアントでログインする。"""

    def _factory(login_id: str) -> TestClient:
        return _login(login_id)

    return _factory


@pytest.fixture()
def client(login_as) -> TestClient:
    """member(yuki)としてログイン済みのクライアント(既存テストの大半をそのまま通す)。"""
    return login_as("yuki")


@pytest.fixture()
def admin_client(login_as) -> TestClient:
    """admin(sensei)としてログイン済みのクライアント。"""
    return login_as("sensei")


@pytest.fixture()
def other_member_client(login_as) -> TestClient:
    """`client`(yuki)とは別のmember(sora)としてログイン済みのクライアント。

    ユーザー間のデータ分離を確認するために使う。
    """
    return login_as("sora")


@pytest.fixture()
def third_member_client(login_as) -> TestClient:
    """`client`(yuki)・`other_member_client`(sora)とは別のmember(haruka)としてログイン
    済みのクライアント。日報シードを持つ新入社員として使う。"""
    return login_as("haruka")


@pytest.fixture()
def anonymous_client(app_client: TestClient) -> TestClient:
    """ログインしていないクライアント。"""
    return TestClient(app)
