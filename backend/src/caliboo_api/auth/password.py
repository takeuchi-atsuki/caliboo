"""パスワードのハッシュ化・検証。

!NOTE: 追加の依存を増やさないため、`passlib`等は使わず標準ライブラリの`hashlib.scrypt`と
       `secrets`だけで実装する。保存形式は`scrypt$n$r$p$salt_b64$hash_b64`で、
       パラメータ(`n`/`r`/`p`)を文字列に含めることで、将来コストパラメータを引き上げても
       既存ハッシュを検証し続けられるようにしている。
"""

import base64
import hashlib
import hmac
import secrets

_ALGORITHM = "scrypt"
_N = 16384
_R = 8
_P = 1
_DKLEN = 32


def _derive(password: str, salt: bytes, n: int, r: int, p: int, dklen: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen)


def hash_password(password: str) -> str:
    """パスワードをランダムsalt付きでハッシュ化し、`scrypt$n$r$p$salt$hash`形式で返す。"""
    salt = secrets.token_bytes(16)
    derived = _derive(password, salt, _N, _R, _P, _DKLEN)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(derived).decode("ascii")
    return f"{_ALGORITHM}${_N}${_R}${_P}${salt_b64}${hash_b64}"


def verify_password(password: str, password_hash: str | None) -> bool:
    """パスワードが`password_hash`と一致するかを検証する。

    形式が不正な`password_hash`(ダミーハッシュ以外で壊れている場合等)・パラメータ不正
    (scryptのコストパラメータが不正で`hashlib.scrypt`が例外を送出する場合等)・
    `password_hash`が`None`のいずれでも、例外を送出せず`False`を返す。
    `hmac.compare_digest`でタイミング攻撃(差分から一致箇所を推測される攻撃)を防ぐ。
    """
    try:
        algorithm, n_str, r_str, p_str, salt_b64, hash_b64 = password_hash.split("$")
        if algorithm != _ALGORITHM:
            return False
        n, r, p = int(n_str), int(r_str), int(p_str)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        derived = _derive(password, salt, n, r, p, len(expected))
    except (ValueError, TypeError, AttributeError):
        return False

    return hmac.compare_digest(derived, expected)


# !NOTE: ログインID不明時でも検証処理そのものは実行し、応答時間の差からログインIDの
#        存在有無が推測されないようにする(`routers/auth.py`参照)。そのためのダミー値を
#        モジュール読み込み時に1回だけ計算しておく(ランダムなパスワードなので誰の
#        パスワードとも一致しない)。
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))
