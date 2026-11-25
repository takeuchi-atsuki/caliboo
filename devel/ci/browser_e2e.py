"""実サーバー・Chromiumでの通常操作スモーク。合成SQLiteだけを利用する。"""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib.metadata import version
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

from playwright.sync_api import Browser, Page, expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
PLAYWRIGHT_VERSION = "1.62.0"
API_PORT = 8000
PREVIEW_PORT = 4173
DEV_PORT = 5173
MEMBER_ID = "ci-smoke-trainee"
MEMBER_NAME = "CI合成新人"
ASSIGNMENT_TITLE = "CI合成課題"
ASSIGNMENT_BODY = "合成データの課題本文を読んで回答する。"
ASSIGNMENT_ANSWER = "合成データの課題に回答しました。"
REPORT_TEXT = (
    "CI合成日報: 手順を整理して確認した。",
    "CI合成日報: 説明の不足に気づいた。",
    "CI合成日報: 次回は例を加える。",
    "CI合成日報: 達成感があった。",
)


def origin(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def child_environment(db: Path) -> dict[str, str]:
    # !NOTE: 親シェルのAIキー・DB接続情報・プロキシ等を引き継がない。
    # PYTHONPATHは明示的なローカルの依存配置を利用する場合に限り親から引き継ぐ。
    names = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH", "PLAYWRIGHT_BROWSERS_PATH")
    env = {name: os.environ[name] for name in names if name in os.environ}
    env.update(
        CALIBOO_SQLITE_PATH=str(db),
        CALIBOO_COOKIE_SECURE="false",
        CALIBOO_DEMO_SEED="true",
        CALIBOO_AI_PROVIDER="manual",
        NODE_OPTIONS="--dns-result-order=ipv4first",
        NO_PROXY="localhost,127.0.0.1",
    )
    return env


def require_free_port(port: int) -> None:
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))


def wait_free_ports(*ports: int, timeout: int = 20) -> None:
    # !NOTE: dev-server.shの親プロセスは、uvicornのreloadワーカーやViteより先に
    # 終了することがある。正常停止後の再起動でポート競合しないよう、解放を確認する。
    deadline = monotonic() + timeout
    while True:
        try:
            for port in ports:
                require_free_port(port)
        except OSError as exc:
            if monotonic() >= deadline:
                raise RuntimeError(f"停止後にE2E用ポートが解放されません: {port}") from exc
            sleep(0.2)
        else:
            return


def wait_http(url: str, processes: list[subprocess.Popen], *, timeout: int = 60) -> None:
    opener = build_opener(ProxyHandler({}))
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError("E2E用のサーバープロセスが起動中に終了しました。")
        try:
            with opener.open(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        sleep(0.2)
    raise RuntimeError(f"E2E用のサーバーが応答しません: {url}")


def stop_group(process: subprocess.Popen) -> None:
    # npm・Viteやuvicornの子プロセスも停止させ、再起動後の確認を別プロセスで行う。
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


@contextmanager
def servers(root: Path, env: dict[str, str], backend_python: str, temp: Path, distribution: bool):
    port = DEV_PORT if distribution else PREVIEW_PORT
    require_free_port(API_PORT)
    require_free_port(port)
    commands = (
        [(root, ["bash", "./devel/dev-server.sh"])]
        if distribution else [
            (root / "backend", [
                backend_python, "-m", "uvicorn", "caliboo_api.main:app",
                "--host", "127.0.0.1", "--port", str(API_PORT),
            ]),
            (root / "frontend", [
                "npm", "run", "preview", "--", "--host", "127.0.0.1",
                "--port", str(port), "--strictPort",
            ]),
        ]
    )
    processes: list[subprocess.Popen] = []
    logs: list[Path] = []
    try:
        for index, (cwd, command) in enumerate(commands):
            log = temp / f"server-{index}.log"
            logs.append(log)
            with log.open("w", encoding="utf-8") as output:
                processes.append(subprocess.Popen(
                    command, cwd=cwd, env={**env, "PYTHON": backend_python},
                    stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
                ))
        wait_http(f"{origin(API_PORT)}/openapi.json", processes)
        wait_http(f"{origin(port)}/", processes)
        yield origin(port)
    except BaseException:
        # ログは毎回生成した合成データのみ。失敗時だけ末尾を表示する。
        for log in logs:
            print(f"--- {log.name} ---", file=sys.stderr)
            print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]),
                  file=sys.stderr)
        raise
    finally:
        for process in reversed(processes):
            stop_group(process)
        if processes:
            wait_free_ports(API_PORT, port)


def initialize_admin(root: Path, python: str, env: dict[str, str]) -> tuple[str, str]:
    login = "ci-smoke-admin"
    password = secrets.token_urlsafe(24)
    env["CALIBOO_DEMO_SEED"] = "false"
    # 通常の初期管理者CLIを使う。合成パスワードを引数・ログに出さない。
    subprocess.run([python, "-m", "caliboo_api.manage", "--login-id", login,
                    "--display-name", "CI合成講師"], cwd=root / "backend", env=env,
                   input=f"{password}\n{password}\n", text=True, capture_output=True,
                   timeout=60, check=True)
    return login, password


@contextmanager
def fresh_page(browser: Browser, base_url: str):
    context = browser.new_context(viewport={"width": 1440, "height": 960}, service_workers="block")
    # !NOTE: ページが参照するCDNのフォント/CSS等は取得しない。画面とAPIは実サーバー。
    context.route("**/*", lambda route: route.continue_()
                  if route.request.url.startswith(base_url + "/") else route.abort())
    page = context.new_page()
    page.set_default_timeout(15_000)
    try:
        yield page
    finally:
        context.close()


def nav(page: Page, label: str):
    navigation = page.get_by_role("navigation", name="メインナビゲーション")
    return navigation.get_by_role("link", name=label, exact=True)


def finish_login(page: Page, login: str, password: str) -> None:
    page.get_by_label("ログインID", exact=True).fill(login)
    page.get_by_label("パスワード", exact=True).fill(password)
    page.get_by_role("button", name="ログイン", exact=True).click()
    expect(page.get_by_role("button", name="ログアウト")).to_be_visible(timeout=30_000)


def login_at_home(page: Page, base: str, login: str, password: str) -> None:
    page.goto(base + "/")
    finish_login(page, login, password)
    expect(page.get_by_role("heading", name="ホーム", exact=True)).to_be_visible()


def create_member(page: Page, password: str, assignment: bool) -> None:
    nav(page, "ユーザー").click()
    expect(page.get_by_role("heading", name="ユーザー管理")).to_be_visible()
    page.get_by_role("button", name="新しいユーザー").click()
    page.get_by_label("ログインID", exact=False).fill(MEMBER_ID)
    page.get_by_label("表示名", exact=False).fill(MEMBER_NAME)
    page.get_by_label("パスワード", exact=False).fill(password)
    page.get_by_role("button", name="保存", exact=True).click()
    expect(page.get_by_role("button", name=MEMBER_NAME, exact=True)).to_be_visible()
    if assignment:
        nav(page, "課題").click()
        page.get_by_role("button", name="課題を作成", exact=True).click()
        dialog = page.get_by_role("dialog")
        dialog.get_by_role("combobox", name="配信先").click()
        page.get_by_role("option", name=MEMBER_NAME, exact=True).click()
        dialog.get_by_placeholder("例: ビジネスメールの書き方をまとめよう").fill(ASSIGNMENT_TITLE)
        dialog.get_by_placeholder("課題の内容を記入してください").fill(ASSIGNMENT_BODY)
        dialog.get_by_role("button", name="作成する").click()
        expect(page.get_by_role("link", name=ASSIGNMENT_TITLE, exact=True)).to_be_visible()
    page.get_by_role("button", name="ログアウト").click()
    expect(page.get_by_role("button", name="ログイン", exact=True)).to_be_visible()
    print("PASS: 講師でログイン、新人アカウントを通常画面で作成", flush=True)


def submit_report(page: Page) -> str:
    nav(page, "日報").click()
    expect(page.get_by_role("heading", name="今日の日報")).to_be_visible()
    form_fields = (
        "例）朝イチでタスクを整理したら集中できた",
        "例）会議の発言タイミングがつかめなかった",
        "例）次の会議で1回は質問してみる",
        "思ったことをそのまま書いてOK。ここはあなただけのスペースだよ。",
    )
    for placeholder, text in zip(form_fields, REPORT_TEXT, strict=True):
        page.get_by_placeholder(placeholder).fill(text)
    page.get_by_role("button", name="うれしい", exact=True).click()
    date = datetime.now(timezone.utc).date().isoformat()
    page.get_by_role("button", name="提出する", exact=True).click()
    expect(page.get_by_text(re.compile(r"提出しました！"))).to_be_visible()
    expect(page.get_by_role("button", name=f"{date}の日報を開く")).to_be_visible()
    print("PASS: 新人でログイン、合成日報を提出", flush=True)
    return date


def verify_report(page: Page, date: str) -> None:
    nav(page, "日報").click()
    page.get_by_role("button", name=f"{date}の日報を開く").click()
    dialog = page.get_by_role("dialog")
    for text in REPORT_TEXT:
        expect(dialog.get_by_text(text, exact=True)).to_be_visible()
    expect(dialog.get_by_text("うれしい", exact=True)).to_be_visible()
    print("PASS: サーバー再起動・新規ブラウザーセッションでも日報の本文ときもちを表示", flush=True)


def verify_assignment(page: Page) -> None:
    nav(page, "強み").click()
    expect(page.get_by_role("heading", name="配信された課題")).to_be_visible()
    page.get_by_role("link", name=ASSIGNMENT_TITLE, exact=True).click()
    expect(page).to_have_url(re.compile(r"/assignments/\d+$"))
    expect(page.get_by_text(ASSIGNMENT_BODY, exact=True)).to_be_visible()
    page.get_by_placeholder("ここに回答を記入してください").fill(ASSIGNMENT_ANSWER)
    page.get_by_role("button", name="提出する", exact=True).click()
    expect(page.get_by_text("回答を提出しました。", exact=True)).to_be_visible()
    page.get_by_role("link", name="課題一覧に戻る").click()
    page.get_by_role("link", name=ASSIGNMENT_TITLE, exact=True).click()
    expect(page.get_by_role("button", name="再提出する")).to_be_visible()
    expect(page.get_by_placeholder("ここに回答を記入してください")).to_have_value(ASSIGNMENT_ANSWER)
    print("PASS: 強みから個人向け配信課題の詳細へ遷移・回答提出・再表示 (#30)", flush=True)


def verify_gui_loading(page: Page, base: str, password: str) -> None:
    # 実配信されたJSの読み込み順を確認する。応答の偽造・タイミング操作はしない。
    requested: list[str] = []
    page.on("request", lambda req: requested.append(Path(urlsplit(req.url).path).name)
            if req.resource_type == "script" and req.url.startswith(base + "/") else None)
    target_url = base + "/home?ci=loading#top"
    started = monotonic()
    page.goto(target_url)
    expect(page.get_by_role("button", name="ログイン", exact=True)).to_be_visible()
    login_ms = (monotonic() - started) * 1000
    if not any(name.startswith("index-") for name in requested):
        raise AssertionError("通常画面の初期JSを取得していません。")
    # #26候補ではログイン・ホーム等の頻出画面は初期JSへ含める場合がある。
    # 未訪問の遅延対象（日報・課題・OJT詳細）を実リクエストで判定する。
    unvisited = ("ReportPage-", "AssignmentDetailPage-", "OjtThreePanePage-")
    if any(name.startswith(unvisited) for name in requested):
        raise AssertionError("認証前に未訪問の画面JSを取得しました。")
    started = monotonic()
    finish_login(page, MEMBER_ID, password)
    expect(page).to_have_url(target_url)
    expect(page.get_by_role("heading", name="ホーム", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="今日のふり返り")).to_be_visible()
    home_ms = (monotonic() - started) * 1000
    if any(name.startswith(unvisited) for name in requested):
        raise AssertionError("未訪問の遅延画面JSを取得しました。")
    started = monotonic()
    nav(page, "日報").click()
    expect(page.get_by_role("heading", name="今日の日報")).to_be_visible()
    report_ms = (monotonic() - started) * 1000
    if not any(name.startswith("ReportPage-") for name in requested):
        raise AssertionError("日報画面JSを遷移時に取得していません。")
    if any(name.startswith(unvisited[1:]) for name in requested):
        raise AssertionError("日報遷移時に未訪問の課題・OJT詳細画面JSまで取得しました。")
    print("PASS: 認証と通常導線に沿った遅延読み込み・URL保持 (#26)", flush=True)
    print(f"画面表示時間（参考値、合否しきい値なし）: 初回ログイン画面={login_ms:.0f} ms / "
          f"認証操作からホームデータ表示={home_ms:.0f} ms / 日報遷移={report_ms:.0f} ms", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="検証対象のチェックアウト・展開済み配布ディレクトリ")
    parser.add_argument("--backend-python", default=sys.executable)
    parser.add_argument("--require-initial-admin", action="store_true", help="デモシード無効で初期管理者CLIを利用")
    parser.add_argument("--distribution", action="store_true", help="配布版の開発サーバー起動手順を検証")
    parser.add_argument("--assignment", action="store_true", help="#30候補の課題導線も必須で検証")
    parser.add_argument("--gui", action="store_true", help="#26候補の画面読み込みも必須で検証（ビルド版）")
    args = parser.parse_args()
    if args.distribution and args.gui:
        parser.error("--gui はビルド版で実行してください。")
    if version("playwright") != PLAYWRIGHT_VERSION:
        parser.error(f"Playwright {PLAYWRIGHT_VERSION} が必要です。")
    root = args.root.resolve(strict=True)
    if not args.distribution and not (root / "frontend/dist/index.html").is_file():
        parser.error("先に frontend で npm run build を実行してください。")
    if args.distribution and not args.require_initial_admin:
        parser.error("配布版は --require-initial-admin も指定してください。")
    if args.distribution and (
        root == ROOT or (root / ".git").exists() or (root / "backend/var").exists()
    ):
        parser.error("配布版検証にはデータ未作成の新規ZIP展開先を --root で指定してください。")

    with TemporaryDirectory(prefix="caliboo-ci-e2e-") as directory:
        temp = Path(directory)
        env = child_environment(temp / "test.sqlite3")
        if args.distribution:
            # #29の配布手順に合わせ、新規ZIP展開先の既定DB（backend/var/caliboo.db）で検証。
            env.pop("CALIBOO_SQLITE_PATH")
        admin = (initialize_admin(root, args.backend_python, env) if args.require_initial_admin
                 else ("sensei", "caliboo-sensei"))
        member_password = secrets.token_urlsafe(24)
        with sync_playwright() as playwright:
            # !NOTE: Playwright既定値に依存せずChromiumのsandboxを明示的に有効にする。
            # sandbox有効で起動できない環境では失敗し、無効化して再試行しない。
            browser = playwright.chromium.launch(chromium_sandbox=True, env=env)
            try:
                print(f"Playwright {PLAYWRIGHT_VERSION} / Chromium {browser.version} / "
                      "sandbox=enabled", flush=True)
                with servers(root, env, args.backend_python, temp, args.distribution) as base:
                    with fresh_page(browser, base) as page:
                        login_at_home(page, base, *admin)
                        create_member(page, member_password, args.assignment)
                    with fresh_page(browser, base) as page:
                        login_at_home(page, base, MEMBER_ID, member_password)
                        date = submit_report(page)
                        if args.assignment:
                            verify_assignment(page)
                with servers(root, env, args.backend_python, temp, args.distribution) as base:
                    with fresh_page(browser, base) as page:
                        login_at_home(page, base, MEMBER_ID, member_password)
                        verify_report(page, date)
                    if args.gui:
                        with fresh_page(browser, base) as page:
                            verify_gui_loading(page, base, member_password)
            finally:
                browser.close()
        if args.distribution and not (root / "backend/var/caliboo.db").is_file():
            raise AssertionError("配布版の既定DBが作成されていません。")
    print("PASS: SQLite実ブラウザーE2E（必須の全操作を完了、skipなし）", flush=True)


if __name__ == "__main__":
    main()
