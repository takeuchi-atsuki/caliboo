"""公開デモ認証情報を運用DBへ投入しない初期化。"""

import pytest

from caliboo_api import manage
from caliboo_api.db import bootstrap_db, session_scope
from caliboo_api.models import User


def test_create_initial_admin_without_demo_users(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CALIBOO_SQLITE_PATH", str(tmp_path / "managed.db"))
    monkeypatch.setattr("sys.argv", ["manage", "--login-id", "admin", "--display-name", "管理者"])
    monkeypatch.setattr(manage.getpass, "getpass", lambda prompt: "long-admin-password")
    manage.main()
    bootstrap_db()
    with session_scope() as session:
        users = session.query(User).all()
        assert len(users) == 1 and users[0].login_id == "admin"
    assert "管理者を作成" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        manage.main()


def test_manage_rejects_invalid_input(monkeypatch):
    monkeypatch.setattr("sys.argv", ["manage", "--login-id", " ", "--display-name", "管理者"])
    with pytest.raises(SystemExit):
        manage.main()
    monkeypatch.setattr("sys.argv", ["manage", "--login-id", "admin", "--display-name", "管理者"])
    monkeypatch.setattr(manage.getpass, "getpass", lambda prompt: "short")
    with pytest.raises(SystemExit):
        manage.main()
