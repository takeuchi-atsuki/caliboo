#!/usr/bin/env python3
"""#26: Calibooの正式ビルドを合成25アカウントの通常閲覧で比較する。"""

import argparse
import json
import math
import os
import re
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PASSWORD = "local-synthetic-fixture-only"
CONTEXTS = 25
DWELL_MS = 2000
FINAL_DWELL_MS = 6000
MIN_AVAILABLE_MB = 1500
NAV = "メインナビゲーション"

# 計測専用プロセス。通常のAPI/表示を変更せず、SQL件数とserver所要時間だけを観測する。
# 外部接続を必要としないfixtureのため、バックエンドからのTCP/IP接続を禁止する。
SERVER = """
import os
import socket
import sys
import time
from contextvars import ContextVar
from pathlib import Path

assert "CALIBOO_DATABASE_URL" not in os.environ
assert os.environ["CALIBOO_AI_PROVIDER"] == "manual"
assert os.environ["CALIBOO_DEMO_SEED"] == "false"
db_path = Path(os.environ["CALIBOO_SQLITE_PATH"])
assert db_path.name == "fixture.db"
assert db_path.parent.name.startswith("caliboo-26-gui-synthetic-")
assert db_path.is_file()

def no_tcp(original):
    def guarded(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise OSError("network disabled in benchmark backend")
        return original(self, address)
    return guarded
socket.socket.connect = no_tcp(socket.socket.connect)
socket.socket.connect_ex = no_tcp(socket.socket.connect_ex)

from sqlalchemy import event
from sqlalchemy.engine import Engine
from caliboo_api.main import app
import uvicorn

counts = ContextVar("benchmark_counts", default=None)

@event.listens_for(Engine, "before_cursor_execute")
def count_sql(conn, cursor, statement, parameters, context, executemany):
    count = counts.get()
    if count is not None:
        count[0] += 1

@app.middleware("http")
async def instrument(request, call_next):
    count = [0]
    token = counts.set(count)
    start = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Benchmark-Queries"] = str(count[0])
        response.headers["X-Benchmark-Server-Ms"] = str((time.perf_counter()-start)*1000)
        return response
    finally:
        counts.reset(token)

uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="error")
"""

ROUTES = {
    "/home": (
        "ホーム", (("GET", "/api/home/summary"),),
    ),
    "/strengths": (
        "強み", (("GET", "/api/development/strengths"), ("GET", "/api/development/actions")),
    ),
    "/assignments": (
        "課題", (("GET", "/api/assignments"),),
    ),
    "/admin/agents": (
        "解析管理", (
            ("GET", "/api/development/jobs"), ("GET", "/api/development/evaluations"),
            ("GET", "/api/development/holdout/cases"),
        ),
    ),
}


def local_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def wait_port(port):
    for _index in range(100):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("local process did not start on its assigned port")


def available_mb():
    path = Path("/proc/meminfo")
    if path.is_file():
        for line in path.read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    return None


def source_env(source):
    env = os.environ.copy()
    env.pop("CALIBOO_DATABASE_URL", None)
    env.pop("CALIBOO_SQLITE_PATH", None)
    env.update(CALIBOO_AI_PROVIDER="manual", CALIBOO_DEMO_SEED="false",
               CALIBOO_COOKIE_SECURE="false", PYTHONDONTWRITEBYTECODE="1")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        path for path in (str(source / "backend/src"), existing) if path
    )
    return env


def make_fixture(env, profile):
    process = subprocess.run(
        [sys.executable, str(ROOT / "devel/measure_gui_api.py"),
         "--prepare-fixture", "--profile", profile],
        cwd=ROOT, env=env, capture_output=True, text=True, check=True, timeout=90,
    )
    return json.loads(process.stdout)


def cleanup_fixture(fixture):
    # 自分が準備した一時DB以外のパスは受け取らない。
    path = Path(fixture["sqlite_path"])
    parent = path.parent
    if (path.name != "fixture.db" or parent.parent != Path(tempfile.gettempdir())
            or not parent.name.startswith("caliboo-26-gui-synthetic-")):
        raise RuntimeError("fixture cleanup refused: unexpected path")
    for suffix in ("", "-wal", "-shm", "-journal"):
        candidate = path.with_name(path.name + suffix)
        candidate.unlink(missing_ok=True)
    parent.rmdir()


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def resource_timing(page, browser_start, required):
    # PerformanceEntryはヘッダー受信直後には未登録の場合があるため、
    # 表示時刻は先に記録したまま、対応するresource timingの採集だけ待つ。
    page.wait_for_function("""({start, paths}) => {
      const completed = performance.getEntriesByType('resource')
        .filter(e => e.startTime >= start && new URL(e.name).origin === location.origin)
        .map(e => new URL(e.name).pathname);
      return paths.every(path => completed.includes(path));
    }""", arg={"start": browser_start, "paths": [path for _, path in required]})
    # URLは自作のローカルoriginのみ。実際のレスポンスbodyやCookieは記録しない。
    return page.evaluate("""start => performance.getEntriesByType('resource')
      .filter(e => {
        const u = new URL(e.name);
        return e.startTime >= start && u.origin === location.origin
          && (u.pathname.endsWith('.js') || u.pathname.startsWith('/api/'));
      })
      .map(e => ({
        path: new URL(e.name).pathname, initiator: e.initiatorType,
        start_ms: Math.round((e.startTime-start)*1000)/1000,
        duration_ms: Math.round(e.duration*1000)/1000,
        transfer_bytes: e.transferSize, encoded_body_bytes: e.encodedBodySize
      }))""", browser_start)


def observe_page(page, base, result):
    events = []

    def on_response(response):
        url = urlparse(response.url)
        if not url.path.startswith("/api/") or f"{url.scheme}://{url.netloc}" != base:
            return
        method = response.request.method
        status = response.status
        result["statuses"][str(status)] += 1
        result["requests"][url.path] += 1
        headers = response.headers
        try:
            server_ms = float(headers["x-benchmark-server-ms"])
            queries = int(headers["x-benchmark-queries"])
        except (KeyError, ValueError):
            result["errors"].append(f"計測用ヘッダーなし: {method} {url.path}")
            return
        if status != 200 and not (url.path == "/api/auth/me" and status == 401):
            result["errors"].append(f"{method} {url.path}: HTTP {status}")
        events.append({
            "method": method, "path": url.path, "status": status, "received": time.perf_counter(),
            "server_ms": round(server_ms, 3), "sql": queries,
        })

    page.on("response", on_response)
    page.on("pageerror", lambda error: result["errors"].append(f"pageerror: {error}"))
    return events


def elapsed_ms(start):
    return round((time.perf_counter() - start) * 1000, 3)


def legacy_marker(page, path):
    # Terraの初回遷移結果に対応するマーカー。強みの見出しだけではデータ準備完了ではない。
    marker = {
        "/home": "今のあなたの強み",
        "/strengths": "強みと成長のヒント",
        "/assignments": "計測用課題-",
        "/admin/agents": "解析管理",
    }[path]
    page.get_by_text(marker, exact=False).first.wait_for()


def data_ready(page, path):
    # 見出しだけでなく、既知の合成データが表示されたことを待つ。
    if path == "/home":
        page.get_by_role("heading", name="今のあなたの強み").wait_for()
    elif path == "/strengths":
        page.get_by_role("heading", name=re.compile("^合成強み-")).first.wait_for()
        page.get_by_role("heading", name="学習手順を整理する").first.wait_for()
        page.get_by_text("計測用課題-", exact=False).first.wait_for()
    elif path == "/assignments":
        page.get_by_text("計測用課題-", exact=False).first.wait_for()
    elif path == "/admin/agents":
        page.get_by_role("heading", name="解析管理").wait_for()
        page.get_by_text("解析待ち", exact=False).first.wait_for()
        page.get_by_text("評価データ不足", exact=False).first.wait_for()


def relevant_api(page, events, begin, required, start):
    # URLが変わっただけでは完了とせず、遷移に対応するAPI応答の観測も待つ。
    deadline = time.monotonic() + 12
    while True:
        found = {}
        for event in events[begin:]:
            key = event["method"], event["path"]
            if key in required and key not in found:
                found[key] = event
        if all(key in found for key in required):
            break
        if time.monotonic() > deadline:
            raise RuntimeError(f"missing API responses: {set(required) - set(found)}")
        page.wait_for_timeout(25)
    responses = []
    for key in required:
        event = found[key]
        responses.append({
            **{k: v for k, v in event.items() if k != "received"},
            "headers_received_ms": round((event["received"] - start) * 1000, 3),
        })
    return responses


def login_form(page, base, events, index):
    start = time.perf_counter()
    begin = len(events)
    page.goto(base + "/login", wait_until="domcontentloaded")
    page.get_by_label("ログインID").wait_for()
    page.locator("input[type=password]").wait_for()
    page.get_by_role("button", name="ログイン", exact=True).wait_for()
    display = elapsed_ms(start)
    api = relevant_api(page, events, begin, (("GET", "/api/auth/me"),), start)
    if api[0]["status"] != 401:
        raise RuntimeError("fresh browser context must be logged out")
    return {
        "user": index, "phase": "login_form_cold", "route": "/login",
        "legacy_marker_ms": display, "display_ms": display, "api": api,
        "resources": resource_timing(page, 0, (("GET", "/api/auth/me"),)),
    }


def measure_transition(page, events, index, phase, path, action, required):
    browser_start = page.evaluate("performance.now()")
    begin = len(events)
    start = time.perf_counter()
    action()
    page.wait_for_url("**" + path)
    legacy_marker(page, path)
    heading = elapsed_ms(start)
    data_ready(page, path)
    api = relevant_api(page, events, begin, required, start)
    if any(item["status"] != 200 for item in api):
        raise RuntimeError("unexpected API status for an ordinary authenticated read")
    display = elapsed_ms(start)
    return {
        "user": index, "phase": phase, "route": path,
        "legacy_marker_ms": heading, "display_ms": display, "api": api,
        "resources": resource_timing(page, browser_start, required),
    }


def navigation(page, events, index, phase, path):
    label, required = ROUTES[path]
    return measure_transition(
        page, events, index, phase, path,
        lambda: page.get_by_role("navigation", name=NAV).get_by_role(
            "link", name=label, exact=True
        ).click(),
        required,
    )


def route_for(index):
    if index == 0:
        return "/admin/agents"
    return "/assignments" if index % 3 == 1 else "/strengths"


def check_running(processes, result):
    memory = available_mb()
    if memory is not None:
        result["min_available_mb"] = min(
            memory, result["min_available_mb"] if result["min_available_mb"] is not None else memory
        )
        if memory < MIN_AVAILABLE_MB:
            raise RuntimeError("insufficient available memory for local browser measurement")
    if any(process.poll() is not None for process in processes):
        raise RuntimeError("a local benchmark process stopped")
    if result["errors"]:
        raise RuntimeError("unexpected page/API error; benchmark stopped")


def browser_measure(base, processes, count, result, browser_executable):
    blocked = set()

    def route_request(route):
        url = urlparse(route.request.url)
        origin = f"{url.scheme}://{url.netloc}"
        if origin == base:
            route.continue_()
        else:
            blocked.add(url.hostname or url.scheme)
            route.abort()

    sessions = []
    try:
        with sync_playwright() as playwright:
            options = {
                "headless": True, "chromium_sandbox": True,
                "args": [
                    "--disable-background-networking", "--disable-component-update",
                    "--disable-sync", "--no-first-run", "--no-proxy-server",
                    "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
                ],
            }
            if browser_executable:
                options["executable_path"] = browser_executable
            browser = playwright.chromium.launch(**options)
            try:
                for index in range(count):
                    check_running(processes, result)
                    context = browser.new_context(
                        viewport={"width": 1360, "height": 900}, locale="ja-JP",
                        service_workers="block",
                    )
                    context.route("**/*", route_request)
                    page = context.new_page()
                    page.set_default_timeout(12000)
                    events = observe_page(page, base, result)
                    sessions.append((context, page, events))
                    result["rows"].append(login_form(page, base, events, index))
                    page.get_by_label("ログインID").fill(f"synthetic-{index:02d}")
                    page.locator("input[type=password]").fill(PASSWORD)
                    result["rows"].append(measure_transition(
                        page, events, index, "login_to_home_cold", "/home",
                        lambda: page.get_by_role("button", name="ログイン", exact=True).click(),
                        (("POST", "/api/auth/login"), ("GET", "/api/home/summary")),
                    ))
                    target = route_for(index)
                    result["rows"].append(navigation(page, events, index, "route_cold", target))
                    result["cold_contexts"] += 1
                    print(f"{result['label']}: cold {index + 1}/{count}",
                          file=sys.stderr, flush=True)
                    # Terraと同じ2秒以上の参加間隔。先に開いたセッションは通常更新を続ける。
                    page.wait_for_timeout(DWELL_MS)
                sessions[-1][1].wait_for_timeout(FINAL_DWELL_MS)
                # 全セッションを開いた状態を維持し、各参加者が通常の間隔で再訪する。
                for index, (_context, page, events) in enumerate(sessions):
                    check_running(processes, result)
                    page.bring_to_front()
                    result["rows"].append(navigation(page, events, index, "route_warm", "/home"))
                    page.wait_for_timeout(DWELL_MS)
                    result["rows"].append(navigation(
                        page, events, index, "route_warm", route_for(index)
                    ))
                    result["warm_contexts"] += 1
                    print(f"{result['label']}: warm {index + 1}/{count}",
                          file=sys.stderr, flush=True)
                    page.wait_for_timeout(DWELL_MS)
                sessions[-1][1].wait_for_timeout(FINAL_DWELL_MS)
                check_running(processes, result)
            finally:
                browser.close()
    finally:
        result["blocked_hosts"] = sorted(blocked)


def stat(values):
    sorted_values = sorted(values)
    return {
        "n": len(values), "p50": round(statistics.median(values), 3),
        "p95": sorted_values[math.ceil(len(values) * 0.95) - 1],
        "max": sorted_values[-1],
    }


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["phase"], row["route"])].append(row)
    summaries = {}
    for (phase, route), group in groups.items():
        apis = defaultdict(list)
        for row in group:
            for api in row["api"]:
                apis[f"{api['method']} {api['path']}"].append(api)
        js_resources = [
            [entry for entry in row["resources"] if entry["path"].endswith(".js")]
            for row in group
        ]
        summaries[f"{phase}:{route}"] = {
            "js_resource_count": stat([len(entries) for entries in js_resources]),
            "js_transfer_bytes": stat([
                sum(entry["transfer_bytes"] for entry in entries)
                for entries in js_resources
            ]),
            "legacy_marker_ms": stat([row["legacy_marker_ms"] for row in group]),
            "display_ms": stat([row["display_ms"] for row in group]),
            "api": {
                name: {
                    "server_ms": stat([item["server_ms"] for item in items]),
                    "headers_received_ms": stat([item["headers_received_ms"] for item in items]),
                    "sql": stat([item["sql"] for item in items]),
                }
                for name, items in apis.items()
            },
        }
    return summaries


def run(args):
    source = args.source.resolve()
    frontend = source / "frontend"
    if (not (frontend / "dist/index.html").is_file()
            or not (source / "backend/src/caliboo_api/main.py").is_file()
            or json.loads((frontend / "package.json").read_text())["name"] != "caliboo-frontend"):
        raise RuntimeError("正式ビルド済みのローカルCalibooチェックアウトを指定してください")
    count = 3 if args.smoke else CONTEXTS
    result = {
        "label": args.label, "profile": args.profile, "contexts_requested": count,
        "cold_contexts": 0, "warm_contexts": 0, "rows": [], "statuses": Counter(),
        "requests": Counter(), "errors": [], "blocked_hosts": [],
        "min_available_mb": available_mb(), "stopped": None,
        "start_load": os.getloadavg() if hasattr(os, "getloadavg") else None,
    }
    start = time.monotonic()
    env = source_env(source)
    fixture = None
    processes = []
    with tempfile.TemporaryDirectory(prefix="caliboo-26-browser-benchmark-") as tmp_name:
        tmp = Path(tmp_name)
        try:
            fixture = make_fixture(env, args.profile)
            result["fixture_rows"] = fixture["table_rows"]
            env["CALIBOO_SQLITE_PATH"] = fixture["sqlite_path"]
            backend_port, frontend_port = local_port(), local_port()
            while backend_port == frontend_port:
                frontend_port = local_port()
            base = f"http://127.0.0.1:{frontend_port}"
            config = tmp / "preview.mjs"
            config.write_text("export default " + json.dumps({
                "root": str(frontend), "envDir": str(tmp),
                "preview": {
                    "host": "127.0.0.1", "port": frontend_port, "strictPort": True,
                    "proxy": {
                        "/api": f"http://127.0.0.1:{backend_port}",
                        "/quiz-assets": f"http://127.0.0.1:{backend_port}",
                    },
                },
            }))
            with (tmp / "server.log").open("w") as log:
                try:
                    processes.append(subprocess.Popen(
                        [sys.executable, "-c", SERVER, str(backend_port)],
                        env=env, stdout=log, stderr=subprocess.STDOUT,
                    ))
                    processes.append(subprocess.Popen(
                        ["node", str(frontend / "node_modules/vite/bin/vite.js"),
                         "preview", "--config", str(config)],
                        cwd=frontend, stdout=log, stderr=subprocess.STDOUT,
                    ))
                    wait_port(backend_port)
                    wait_port(frontend_port)
                    browser_measure(base, processes, count, result, args.browser_executable)
                finally:
                    for process in reversed(processes):
                        stop_process(process)
        except Exception as error:
            result["stopped"] = f"{type(error).__name__}: {error}"
        finally:
            if fixture is not None:
                cleanup_fixture(fixture)
        result["summary"] = summarize(result["rows"])
        result["elapsed_s"] = round(time.monotonic() - start, 3)
        result["end_load"] = os.getloadavg() if hasattr(os, "getloadavg") else None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT,
                        help="正式ビルド済みのローカルCalibooチェックアウト")
    parser.add_argument("--label", required=True, help="比較結果の識別子")
    parser.add_argument("--profile", choices=("small", "populated"), default="populated")
    parser.add_argument("--smoke", action="store_true", help="3コンテキストの動作確認だけ行う")
    parser.add_argument("--browser-executable", help="ローカルのChromium実行ファイル（省略可）")
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["stopped"] or result["errors"] or (
        result["cold_contexts"] != result["contexts_requested"]
        or result["warm_contexts"] != result["contexts_requested"]
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
