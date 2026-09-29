"""ローカル開発環境の登録アカウントを読み取り専用で一覧表示する。"""

import argparse
import getpass
import http.cookiejar
import json
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://localhost:8000"
FIELDS = ("id", "loginId", "displayName", "role", "active", "departmentId")


class UserListError(Exception):
    """利用者に表示してよいエラーメッセージ。"""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def validate_base_url(value):
    """Cookieをローカル開発サーバー以外へ送らない。"""
    parsed = urllib.parse.urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise UserListError("接続先のポート番号が不正です。") from error
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or port is None
    ):
        raise UserListError("接続先はポート付きのローカルHTTP URLに限ります。")
    return value.rstrip("/")


def request_json(opener, base_url, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {} if data is None else {"Content-Type": "application/json"}
    request = urllib.request.Request(
        base_url + path, data=data, headers=headers,
        method="GET" if data is None else "POST",
    )
    with opener.open(request, timeout=10) as response:
        return None if response.status == 204 else json.load(response)


def list_users(base_url, login_id, password):
    """ログイン後に管理者APIを読み、表示に必要な項目のみ返す。"""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPCookieProcessor(jar),
        NoRedirect(),
    )
    logged_in = False
    try:
        try:
            request_json(opener, base_url, "/api/auth/login", {
                "loginId": login_id, "password": password,
            })
            logged_in = True
        except urllib.error.HTTPError as error:
            if error.code == 401:
                raise UserListError("認証失敗 (401): ログインIDまたはパスワードを確認してください。") from None
            raise UserListError(f"ログインAPIがHTTP {error.code}を返しました。") from None

        try:
            payload = request_json(opener, base_url, "/api/users")
        except urllib.error.HTTPError as error:
            if error.code == 403:
                raise UserListError("権限不足 (403): 一覧表示には管理者アカウントが必要です。") from None
            if error.code == 401:
                raise UserListError("セッションが無効です (401)。再ログインしてください。") from None
            raise UserListError(f"ユーザー一覧APIがHTTP {error.code}を返しました。") from None
        users = payload.get("users") if isinstance(payload, dict) else None
        if not isinstance(users, list) or any(not isinstance(user, dict) for user in users):
            raise UserListError("ユーザー一覧APIの応答形式が不正です。")
        return [{field: user.get(field) for field in FIELDS} for user in users]
    except (urllib.error.URLError, TimeoutError) as error:
        raise UserListError("ローカルAPIへ接続できません。サーバーの起動を確認してください。") from error
    except (ValueError, UnicodeError) as error:
        raise UserListError("APIのJSON応答を読めません。") from error
    finally:
        if logged_in:
            try:
                request_json(opener, base_url, "/api/auth/logout", {})
            except (urllib.error.URLError, TimeoutError, ValueError, UnicodeError):
                pass
        jar.clear()


def format_table(users):
    def width(value):
        return sum(2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1 for char in value)

    def pad(value, target):
        return value + " " * (target - width(value))

    columns = ("ID", "ログインID", "表示名", "権限", "有効", "部署ID")
    rows = [
        (
            str(user["id"]), str(user["loginId"]), str(user["displayName"]),
            str(user["role"]), "はい" if user["active"] else "いいえ",
            str(user["departmentId"] or "-"),
        )
        for user in users
    ]
    widths = [
        max(width(str(row[index])) for row in [columns, *rows])
        for index in range(len(columns))
    ]
    lines = ["  ".join(pad(label, widths[index]) for index, label in enumerate(columns))]
    lines.extend(
        "  ".join(pad(value, widths[index]) for index, value in enumerate(row))
        for row in rows
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Calibooの登録アカウント一覧を表示します。")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="ローカル開発サーバーのURL")
    parser.add_argument("--login-id", default="sensei", help="管理者のログインID")
    parser.add_argument("--demo", action="store_true", help="公開開発シードの管理者で実行")
    parser.add_argument("--format", choices=("table", "json"), default="table")
    args = parser.parse_args(argv)
    try:
        base_url = validate_base_url(args.base_url)
        if args.demo and args.login_id != "sensei":
            raise UserListError("--demoは公開開発シードのsensei専用です。")
        # 開発用公開シードのみ。通常利用ではパスワードを引数やファイルへ保存しない。
        password = "caliboo-sensei" if args.demo else getpass.getpass("パスワード: ")
        users = list_users(base_url, args.login_id, password)
        output = (
            json.dumps(users, ensure_ascii=False, indent=2)
            if args.format == "json" else format_table(users)
        )
        print(output)
        return 0
    except (UserListError, EOFError, KeyboardInterrupt) as error:
        message = str(error) if isinstance(error, UserListError) else "入力を中断しました。"
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
