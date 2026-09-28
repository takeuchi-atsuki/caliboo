"""ローカルCalibooのエージェントキュー入出力。LLM APIは使用しない。"""

import argparse
import getpass
import http.cookiejar
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--login-id", default="sensei")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("action", choices=["list", "export", "import"])
    parser.add_argument("job_id", type=int, nargs="?")
    parser.add_argument("file", type=Path, nargs="?")
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.base_url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.scheme != "http":
        parser.error("base-url must be a local HTTP server")
    if args.action != "list" and (args.job_id is None or args.file is None):
        parser.error("export/import requires JOB_ID FILE")
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(path: str, body: dict | None = None):
        request = urllib.request.Request(
            args.base_url.rstrip("/") + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
        )
        with opener.open(request, timeout=30) as response:
            return json.load(response)

    password = "caliboo-sensei" if args.demo else getpass.getpass("Password: ")
    try:
        call("/api/auth/login", {"loginId": args.login_id, "password": password})
        if args.action == "list":
            result = call("/api/development/jobs")
        else:
            job = call(f"/api/development/jobs/{args.job_id}")
            if args.action == "export":
                packet = job
                if job["kind"] == "strength":
                    # !NOTE: 解析に不要な本人ID・既存結果をエージェントへ渡さない。
                    packet = {
                        "inputSchema": call("/api/development/strength-materials/schema"),
                        "materials": job["materials"],
                    }
                args.file.write_text(
                    json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
                result = {"exported": args.job_id, "file": str(args.file)}
            else:
                payload = json.loads(args.file.read_text(encoding="utf-8"))
                path = (f"/api/development/jobs/{args.job_id}/strength-result"
                        if job["kind"] == "strength"
                        else f"/api/assignment-proposals/agent-jobs/{args.job_id}/result")
                result = call(path, payload)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except urllib.error.HTTPError as error:
        parser.exit(1, f"HTTP {error.code}: {error.read().decode()}\n")


if __name__ == "__main__":
    main()
