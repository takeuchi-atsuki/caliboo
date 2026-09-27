"""パスワードハッシュ化・検証(`auth/password.py`)の実装テスト。"""

import re

from caliboo_api.auth import password


def test_hash_password_matches_expected_format():
    hashed = password.hash_password("some-password")

    assert re.fullmatch(r"scrypt\$\d+\$\d+\$\d+\$[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+", hashed)


def test_hash_password_uses_random_salt():
    first = password.hash_password("same-password")
    second = password.hash_password("same-password")

    assert first != second
    assert first.split("$")[4] != second.split("$")[4]


def test_verify_password_succeeds_for_correct_password():
    hashed = password.hash_password("correct-password")

    assert password.verify_password("correct-password", hashed) is True


def test_verify_password_fails_for_wrong_password():
    hashed = password.hash_password("correct-password")

    assert password.verify_password("wrong-password", hashed) is False


def test_verify_password_fails_for_malformed_hash():
    assert password.verify_password("anything", "not-a-valid-hash") is False


def test_verify_password_fails_for_none_hash():
    """`password_hash`が`None`(未設定アカウント)でも例外を出さず`False`を返す。"""
    assert password.verify_password("anything", None) is False


def test_verify_password_fails_for_unknown_algorithm_tag():
    hashed = password.hash_password("correct-password")
    tampered = hashed.replace("scrypt$", "md5$", 1)

    assert password.verify_password("correct-password", tampered) is False


def test_dummy_password_hash_has_valid_format_and_matches_no_real_password():
    assert re.fullmatch(
        r"scrypt\$\d+\$\d+\$\d+\$[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+",
        password.DUMMY_PASSWORD_HASH,
    )
    assert password.verify_password("caliboo-yuki", password.DUMMY_PASSWORD_HASH) is False


def test_login_with_unknown_user_still_calls_verify_password(anonymous_client, monkeypatch):
    """ログインIDが存在しなくても検証関数が呼ばれる(応答時間からIDの存在を推測させないため)。"""
    calls = []
    original_verify = password.verify_password

    def _spy(raw_password: str, password_hash: str) -> bool:
        calls.append((raw_password, password_hash))
        return original_verify(raw_password, password_hash)

    monkeypatch.setattr(password, "verify_password", _spy)

    response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "no-such-user", "password": "whatever"}
    )

    assert response.status_code == 401
    assert calls == [("whatever", password.DUMMY_PASSWORD_HASH)]
