"""限定試用の正式ビルド + HTTPS実サーバーの通常フロー（合成値のみ）。"""

import argparse
from base64 import b64encode
from contextlib import contextmanager
from http.cookiejar import CookieJar
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPCookieProcessor, HTTPSHandler, ProxyHandler, Request, build_opener,
)

ROOT = Path(__file__).resolve().parents[2]
GATE = "sample-access-for-test-only-01"
INSTRUCTOR = "sample-instructor-only-01"
MEMBER = "sample-member-only-01"
REPORT = {
    "date": "2026-11-25",
    "keep": "HTTPS合成演習: 一つの手順を確認",
    "problem": "HTTPS合成演習: 説明を追加する",
    "try": "HTTPS合成演習: 次の架空例を確認する",
    "status": "submitted",
}


def free_port():
    with socket.socket() as local_socket:
        local_socket.bind(("127.0.0.1", 0))
        return local_socket.getsockname()[1]


def test_certificate(directory):
    """試験ごとに生成するローカル専用証明書だけをクライアントで信頼する。"""
    cert, key = (directory / "cert.pem", directory / "key.pem")
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-sha256", "-nodes",
        "-keyout", str(key), "-out", str(cert), "-days", "1",
        "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1",
    ], check=True, capture_output=True)
    return cert, key


class Client:
    def __init__(self, base, cert, *, gate=True):
        self.base = base
        self.headers = {}
        if gate:
            self.headers["Authorization"] = "Basic " + b64encode(
                f"trial:{GATE}".encode("ascii"),
            ).decode("ascii")
        self.opener = build_opener(
            ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context(cafile=str(cert))),
            HTTPCookieProcessor(CookieJar()),
        )

    def request(self, path, *, payload=None, method="GET", status=200):
        headers = self.headers.copy()
        if method != "GET":
            headers["Origin"] = self.base
        if payload is not None:
            headers["Content-Type"] = "application/json"
        with_status = Request(
            self.base + path,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers=headers, method=method,
        )
        try:
            response = self.opener.open(with_status, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            assert response.status == status, f"{method} {path}: HTTP {response.status}"
            return response.read(), response.headers

    def get_json(self, path):
        return json.loads(self.request(path)[0])

    def post_json(self, path, payload):
        return json.loads(self.request(path, payload=payload, method="POST")[0])

    def login(self, login, password):
        body, headers = self.request(
            "/api/auth/login", method="POST", payload={"loginId": login, "password": password},
        )
        cookie = headers["Set-Cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie
        return json.loads(body)

    def logout(self):
        self.request("/api/auth/logout", method="POST", status=204)
        self.request("/api/auth/me", status=401)


class EntryScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            location = dict(attrs).get("src")
            if location:
                self.scripts.append(location)


@contextmanager
def server(root, python, directory, cert, key, label):
    """子プロセスで試用入口そのものを起動し、専用ログ・ポートを利用する。"""
    port = free_port()
    base = f"https://127.0.0.1:{port}"
    env = {
        name: os.environ[name]
        for name in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PYTHONPATH")
        if name in os.environ
    }
    env.update(
        CALIBOO_TRIAL_ORIGIN=base,
        CALIBOO_TRIAL_ACCESS_PASSWORD=GATE,
        CALIBOO_TRIAL_INSTRUCTOR_PASSWORD=INSTRUCTOR,
        CALIBOO_TRIAL_MEMBER_PASSWORD=MEMBER,
        CALIBOO_TRIAL_TLS_CERTFILE=str(cert),
        CALIBOO_TRIAL_TLS_KEYFILE=str(key),
        CALIBOO_AI_PROVIDER="manual",
        CALIBOO_DEMO_SEED="false",
        CALIBOO_COOKIE_SECURE="true",
        PORT=str(port),
    )
    with (directory / (label + ".log")).open("w+", encoding="utf-8") as log:
        process = subprocess.Popen(
            [python, "-m", "caliboo_api.trial"], cwd=root, env=env,
            stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            anonymous = Client(base, cert, gate=False)
            deadline = monotonic() + 30
            while monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("試用サーバーが起動中に終了しました")
                try:
                    assert anonymous.get_json("/healthz") == {"status": "ok"}
                    break
                except (URLError, OSError):
                    sleep(0.25)
            else:
                raise RuntimeError("試用サーバーが応答しません")
            yield base
        except BaseException:
            log.seek(0)
            print(log.read(), file=sys.stderr)
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--backend-python", default=sys.executable)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if not (root / "frontend/dist/index.html").is_file():
        parser.error("限定試用の正式 frontend build が必要です")
    with TemporaryDirectory(prefix="caliboo-trial-ci-") as temp:
        directory = Path(temp)
        cert, key = test_certificate(directory)
        with server(root, args.backend_python, directory, cert, key, "first") as base:
            anonymous = Client(base, cert, gate=False)
            anonymous.request("/", status=401)
            instructor = Client(base, cert)
            index = instructor.request("/")[0]
            assert instructor.request("/home")[0] == index
            links = EntryScripts()
            links.feed(index.decode("utf-8"))
            assert links.scripts
            for path in links.scripts:
                assert urlsplit(path).netloc == "" and path.startswith("/")
                asset, _headers = instructor.request(path)
                assert len(asset) > 0
            assert b"<svg" in instructor.request("/quiz-assets/wave-a.svg")[0]
            print("PASS: TLS信頼・匿名healthz・試用制限・同一オリジン正式成果物", flush=True)
            assert instructor.login("trial-instructor", INSTRUCTOR)["role"] == "admin"
            assert instructor.get_json("/api/development/jobs")["provider"] == "manual"
            member = Client(base, cert)
            assert member.login("trial-member", MEMBER)["role"] == "member"
            assert member.get_json("/api/home/summary")
            assert member.get_json("/api/report/history")["history"] == []
            assert member.post_json("/api/report", REPORT)["status"] == "submitted"
            assert any(
                job["kind"] == "strength"
                for job in instructor.get_json("/api/development/jobs")["jobs"]
            )
            member.logout()
            member = Client(base, cert)
            member.login("trial-member", MEMBER)
            assert member.get_json("/api/report/history")["history"][0]["keep"] == REPORT["keep"]
            member.logout()
            instructor.logout()
            print("PASS: 講師/新人ログイン・manual日報・同一プロセス保存・ログアウト", flush=True)
        with server(root, args.backend_python, directory, cert, key, "restart") as base:
            member = Client(base, cert)
            member.login("trial-member", MEMBER)
            assert member.get_json("/api/report/history")["history"] == []
            member.logout()
            print("PASS: 別プロセス再起動で合成初期状態へ戻る", flush=True)
    print("PASS: 限定試用入口HTTPS実サーバー通常フロー（ブラウザー描画は対象外）", flush=True)


if __name__ == "__main__":
    main()
