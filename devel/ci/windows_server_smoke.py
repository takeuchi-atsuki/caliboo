"""Windowsの新規配布ZIP: Git Bashの実起動、通常画面操作、再起動の品質ゲート。"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[2]
API = "http://127.0.0.1:8000"
WEB = "http://127.0.0.1:5173"
PORTS = (8000, 5173)
PLAYWRIGHT_VERSION = "1.62.0"
ADMIN_LOGIN = "ci-smoke-admin"
MEMBER_LOGIN = "ci-smoke-trainee"
MEMBER_NAME = "CI合成新人"
REPORT = {
    "keep": "CI合成日報: 手順を整理して確認した。",
    "problem": "CI合成日報: 説明の不足に気づいた。",
    "try": "CI合成日報: 次回は例を加える。",
    "moodComment": "CI合成日報: 達成感があった。",
    "mood": ["happy"],
}


class GateError(RuntimeError):
    """ログに出してよい固定メッセージを持つ検証失敗。"""


def clean_environment() -> dict[str, str]:
    # Windows・Git Bash・Node・Chromiumの起動に必要なOS環境だけを引き継ぐ。
    names = (
        "PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "USERPROFILE", "HOME", "LOCALAPPDATA",
        "APPDATA", "HOMEDRIVE", "HOMEPATH", "COMSPEC", "PATHEXT", "PROGRAMFILES",
        "PROGRAMFILES(X86)", "PROGRAMW6432", "PROGRAMDATA", "ALLUSERSPROFILE", "LANG", "LC_ALL",
        "PLAYWRIGHT_BROWSERS_PATH", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
    )
    env = {name: os.environ[name] for name in names if name in os.environ}
    # !NOTE: 配布版手順の既定SQLiteを使う。外部AI、DB URL、代理接続、認証情報は継承しない。
    env.update(CALIBOO_DEMO_SEED="false", CALIBOO_AI_PROVIDER="manual",
               CALIBOO_COOKIE_SECURE="false", NODE_OPTIONS="--dns-result-order=ipv4first",
               NO_PROXY="127.0.0.1,localhost", PYTHONUTF8="1")
    return env


def initialize_admin(root: Path, python: Path, env: dict[str, str]) -> str:
    password = secrets.token_urlsafe(24)
    # !NOTE: Windowsのgetpassはconsole入力を利用する。非対話CIではstdinを別の
    # ストリームにしてgetpass標準のstdin fallbackを選び、実際の管理CLIをそのまま実行する。
    # 合成パスワードはstdinだけで受け渡しし、既定のstdout/stderrもログに保存しない。
    cli = ("import io,runpy,sys; sys.stdin=io.StringIO(sys.stdin.read()); "
           "runpy.run_module('caliboo_api.manage',run_name='__main__')")
    result = subprocess.run(
        [str(python), "-c", cli, "--login-id", ADMIN_LOGIN, "--display-name", "CI合成講師"],
        cwd=root / "backend", env=env, text=True, encoding="utf-8",
        input=f"{password}\n{password}\n", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=60, check=False,
    )
    if result.returncode != 0:
        raise GateError(f"初期管理者CLIが失敗しました (exit={result.returncode})")
    print("PASS: 合成管理者を配布版の既存CLIで作成", flush=True)
    return password


def port_listening(port: int) -> bool:
    with socket.socket() as connection:
        connection.settimeout(0.5)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def wait_ports_released(timeout: float = 20) -> None:
    deadline = monotonic() + timeout
    while any(port_listening(port) for port in PORTS):
        if monotonic() >= deadline:
            raise GateError("所有サーバー停止後、8000/5173のポートが解放されません")
        sleep(0.2)


def wait_url(url: str, process: subprocess.Popen, *, timeout: float = 120) -> None:
    opener = build_opener(ProxyHandler({}))
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if process.poll() is not None:
            raise GateError(f"Windows配布版の起動プロセスが終了 (exit={process.returncode})")
        try:
            with opener.open(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (URLError, OSError):
            pass
        sleep(0.3)
    raise GateError(f"Windows配布版起動タイムアウト: {url}")


def terminate_owned_tree(process: subprocess.Popen, env: dict[str, str]) -> None:
    # !NOTE: Git Bashを終了するだけではWindows Pythonのsupervisorが残り得る。
    # 配布版のjob objectと、自分で起動したPIDの子孫だけを対象とするtaskkillを併用する。
    # ポートを使用している未知のPIDを調べたり停止したりしない。
    mode = "already-exited"
    if process.poll() is None:
        mode = "CTRL_BREAK_EVENT"
        try:
            process.send_signal(signal.CTRL_BREAK_EVENT)
            process.wait(timeout=8)
        except (OSError, subprocess.TimeoutExpired):
            pass
    if process.poll() is None:
        mode = "owned-tree-taskkill"
        taskkill = Path(env["SystemRoot"]) / "System32" / "taskkill.exe"
        result = subprocess.run([str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=15, check=False)
        if result.returncode != 0 and process.poll() is None:
            raise GateError(f"所有サーバープロセス群の停止に失敗 (exit={result.returncode})")
        process.wait(timeout=15)
    wait_ports_released()
    # CTRL_BREAKやCIのtree停止は、利用者の対話Ctrl+Cの検証とは別。
    print(f"INFO: Windows CIサーバー停止方式={mode}", flush=True)


@contextmanager
def windows_servers(root: Path, git_bash: Path, env: dict[str, str]):
    if any(port_listening(port) for port in PORTS):
        raise GateError("8000/5173に既存サービスがあるため開始しません")
    # Windows版配布手順の入口。Pythonはそのスクリプトの既定venvを使う。
    command = [str(git_bash), "--noprofile", "--norc", "./devel/windows/dev-server-windows.sh"]
    process = subprocess.Popen(command, cwd=root, env=env,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    try:
        wait_url(API + "/openapi.json", process)
        wait_url(WEB + "/", process)
        print("PASS: Windows Git Bash配布版の実サーバー起動", flush=True)
        yield WEB
    finally:
        terminate_owned_tree(process, env)
        print("PASS: 所有サーバープロセス群停止・ポート解放", flush=True)


def check_html_entries(base: str) -> None:
    opener = build_opener(ProxyHandler({}))
    entries = {"/": "<title>Caliboo</title>",
               "/takeuchi-model.html": "<title>Caliboo マスコット 3D モデル</title>"}
    for path, title in entries.items():
        with opener.open(base + path, timeout=15) as response:
            if response.status != 200 or title not in response.read().decode("utf-8"):
                raise GateError(f"HTMLの通常入口が一致しません: {path}")
    print("PASS: メイン画面・3Dモデルの2入口HTTP 200", flush=True)


def api_client():
    return build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))


def api_call(client, base: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(base + path, data=data, headers={"Content-Type": "application/json"})
    with client.open(request, timeout=15) as response:
        return json.load(response) if response.status != 204 else None


def login(client, base: str, username: str, password: str, role: str) -> dict:
    user = api_call(client, base, "/api/auth/login", {"loginId": username, "password": password})
    if user["loginId"] != username or user["role"] != role:
        raise GateError("通常ログインでユーザーまたはロールが一致しません")
    return user


def check_clean_admin(base: str, admin_password: str) -> None:
    client = api_client()
    login(client, base, ADMIN_LOGIN, admin_password, "admin")
    users = api_call(client, base, "/api/users")["users"]
    if len(users) != 1 or users[0]["loginId"] != ADMIN_LOGIN:
        raise GateError("新規配布DBに想定外のアカウントが存在します")
    api_call(client, base, "/api/auth/logout", {})
    print("PASS: デモユーザーなし・合成管理者のみ", flush=True)


def api_smoke(server, admin_password: str, member_password: str) -> None:
    """ブラウザー未利用時のみ、通常HTTP操作を部分確認する（UI合格とはしない）。"""
    with server() as base:
        check_html_entries(base)
        check_clean_admin(base, admin_password)
        client = api_client()
        login(client, base, ADMIN_LOGIN, admin_password, "admin")
        api_call(client, base, "/api/users", {
            "loginId": MEMBER_LOGIN, "displayName": MEMBER_NAME,
            "password": member_password, "role": "member",
        })
        api_call(client, base, "/api/auth/logout", {})
        login(client, base, MEMBER_LOGIN, member_password, "member")
        api_call(client, base, "/api/home/summary")
        date = datetime.now(timezone.utc).date().isoformat()
        submitted = api_call(client, base, "/api/report", {**REPORT, "date": date,
                                                           "status": "submitted"})
        if submitted["status"] != "submitted":
            raise GateError("合成日報の提出状態が一致しません")
        api_call(client, base, "/api/auth/logout", {})
        print("PARTIAL PASS: 通常HTTPによる合成新人作成・日報提出", flush=True)
    with server() as base:
        check_html_entries(base)
        client = api_client()
        login(client, base, MEMBER_LOGIN, member_password, "member")
        history = api_call(client, base, "/api/report/history")["history"]
        if not any(item["date"] == date and all(item[key] == value for key, value in REPORT.items())
                   for item in history):
            raise GateError("再起動後の合成日報履歴が一致しません")
        api_call(client, base, "/api/auth/logout", {})
        print("PARTIAL PASS: Windows実サーバー再起動・新規セッションの日報永続化 (HTTP)",
              flush=True)


def run_ui_if_available(server, env: dict[str, str], admin_password: str,
                        member_password: str) -> bool:
    # Playwright導入が失敗しても通常APIの証跡は記録する。実ブラウザー操作失敗の場合は
    # ここでfallbackせず例外を伝え、UI検証失敗として終了する。
    try:
        installed = version("playwright")
    except PackageNotFoundError:
        print("UNVERIFIED UI: Playwright未導入", flush=True)
        return False
    if installed != PLAYWRIGHT_VERSION:
        print("UNVERIFIED UI: Playwright固定版が未導入", flush=True)
        return False
    try:
        from playwright.sync_api import Error, sync_playwright
        import browser_e2e as e2e
    except ImportError:
        print("UNVERIFIED UI: Playwrightの読み込み不可", flush=True)
        return False
    try:
        playwright = sync_playwright().start()
    except (Error, OSError):
        print("UNVERIFIED UI: Playwrightドライバー起動不可", flush=True)
        return False
    try:
        try:
            browser = playwright.chromium.launch(chromium_sandbox=True, env=env)
        except (Error, OSError):
            print("UNVERIFIED UI: 固定Chromiumをsandbox有効で起動不可", flush=True)
            return False
        try:
            print(f"Playwright {installed} / Chromium {browser.version} / sandbox=enabled",
                  flush=True)
            print("START: Windows実ブラウザー通常操作", flush=True)
            with server() as base:
                check_html_entries(base)
                check_clean_admin(base, admin_password)
                with e2e.fresh_page(browser, base) as page:
                    e2e.login_at_home(page, base, ADMIN_LOGIN, admin_password)
                    e2e.create_member(page, member_password, False)
                with e2e.fresh_page(browser, base) as page:
                    e2e.login_at_home(page, base, MEMBER_LOGIN, member_password)
                    date = e2e.submit_report(page)
            with server() as base:
                check_html_entries(base)
                with e2e.fresh_page(browser, base) as page:
                    e2e.login_at_home(page, base, MEMBER_LOGIN, member_password)
                    e2e.verify_report(page, date)
        finally:
            browser.close()
    finally:
        playwright.stop()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="クリーンZIP展開先")
    parser.add_argument("--git-bash", type=Path, required=True, help="WindowsのGit Bash実行ファイル")
    parser.add_argument("--backend-python", type=Path, help="展開先backend/.venv/Scripts/python.exe")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Windows runnerのネイティブPythonから実行してください")
    try:
        root = args.root.resolve(strict=True)
        git_bash = args.git_bash.resolve(strict=True)
        python = (root / "backend/.venv/Scripts/python.exe").resolve(strict=True)
        if args.backend_python and args.backend_python.resolve(strict=True) != python:
            raise GateError("展開先でsetupした既定Windows venv以外は利用しません")
        if root == ROOT or (root / ".git").exists() or (root / "backend/var").exists():
            raise GateError("既存DBやcheckoutではなく、データ未作成の新規ZIP展開先が必要です")
        if not (root / "devel/windows/dev-server-windows.sh").is_file() or not git_bash.is_file():
            raise GateError("Windows配布用起動スクリプトまたはGit Bashが不足しています")
        if not all((root / "frontend/dist" / name).is_file()
                   for name in ("index.html", "takeuchi-model.html")):
            raise GateError("先に展開先で2入口をビルドしてください")
        env = clean_environment()
        if "SystemRoot" not in env:
            raise GateError("Windows起動に必要なSystemRootがありません")
        print("START: Windows配布版 初期管理者CLI", flush=True)
        admin_password = initialize_admin(root, python, env)
        member_password = secrets.token_urlsafe(24)

        def server():
            return windows_servers(root, git_bash, env)

        ui_verified = run_ui_if_available(server, env, admin_password, member_password)
        if not ui_verified:
            print("START: UI不可時の通常HTTP部分検証", flush=True)
            api_smoke(server, admin_password, member_password)
        if not (root / "backend/var/caliboo.db").is_file():
            raise GateError("展開先既定SQLiteが作成されていません")
        if not ui_verified:
            print("INCOMPLETE: Windows通常HTTP部分成功・実ブラウザー未確認（CI失敗）",
                  file=sys.stderr, flush=True)
            return 1
        print("PASS: Windows配布版の実ブラウザー・再起動検証（skipなし）", flush=True)
        return 0
    except GateError as failure:
        print(f"FAIL: {failure}", file=sys.stderr, flush=True)
    except Exception as failure:
        # Playwright/CLI/HTTPの生ログやリクエスト本文は公開CIへ出さない。
        print(f"FAIL: Windows配布版の必須検証で {type(failure).__name__}",
              file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
