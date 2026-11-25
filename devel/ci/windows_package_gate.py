"""Windows x64 / Git Bash の #29 配布候補を新規展開して検証する。"""

import argparse
import json
import os
from pathlib import Path
import platform
import re
import struct
import subprocess
import sys
import tempfile
import zipfile

from package_gate import GateError, clean_environment, require, validate_archive
from quality_gate import validate_node


ROOT = Path(__file__).resolve().parents[2]
CI_DIR = Path(__file__).resolve().parent
WINDOWS_SCRIPTS = {
    "Caliboo/devel/windows/build-windows.sh",
    "Caliboo/devel/windows/setup-windows.sh",
    "Caliboo/devel/windows/dev-server-windows.sh",
}
TOKYO_CHECK = """
from datetime import datetime, timezone
from importlib.metadata import version
import json
import platform
import struct
import sys
from zoneinfo import TZPATH, ZoneInfo

source = datetime(2026, 1, 1, 3, 4, 5, tzinfo=timezone.utc)
local = source.astimezone(ZoneInfo("Asia/Tokyo"))
print(json.dumps({
    "native_x64": sys.platform == "win32" and struct.calcsize("P") == 8
                  and platform.machine().upper() in {"AMD64", "X86_64"},
    "venv": sys.prefix != sys.base_prefix,
    "no_system_tzpath": not TZPATH,
    "tokyo": local.isoformat(),
    "tzdata": version("tzdata"),
}))
"""


def require_native_windows():
    require(sys.platform == "win32" and struct.calcsize("P") == 8
            and platform.machine().upper() in {"AMD64", "X86_64"},
            "Windows x64のネイティブPythonが必要です（WSL/ARM64は対象外）。")
    require(sys.version_info[:2] == (3, 12), "Python 3.12 が必要です。")


def run_captured(label, command, *, cwd, environment, timeout):
    # !NOTE: 依存導入ツール等の生ログは出さない。ステージ・終了コードだけを表示する。
    try:
        result = subprocess.run(
            [str(part) for part in command], cwd=cwd, env=environment,
            check=False, capture_output=True, timeout=timeout,
            text=True, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        raise GateError(f"{label}: タイムアウト") from None
    except OSError:
        raise GateError(f"{label}: プロセスを起動できませんでした。") from None
    require(result.returncode == 0, f"{label}: 終了コード {result.returncode}")
    return result.stdout.strip()


def find_git_bash(configured, root, environment):
    # !NOTE: WindowsのPATH先頭のbash.exeがWSLである可能性がある。
    # 標準runnerのGit for Windowsを明示し、Git Bashのuname/cygpathで確認する。
    if configured is None:
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        configured = Path(program_files) / "Git/bin/bash.exe"
    bash = configured.resolve()
    require(bash.is_file() and bash.name.lower() == "bash.exe",
            "Git for Windowsのbash.exeを指定してください。")
    command = 'case "$(uname -s)" in MINGW*|MSYS*) cygpath -u "$1";; *) exit 1;; esac'
    converted = run_captured(
        "Git Bashの確認", [bash, "-c", command, "caliboo-ci", sys.executable],
        cwd=root, environment=environment, timeout=20,
    )
    require(converted.startswith("/") and "\n" not in converted and "\r" not in converted,
            "Git Bash内でWindows Python実行ファイルのパスを取得できません。")
    return bash, converted


def verify_node(root, bash, environment):
    command = """node -p 'JSON.stringify({
        platform: process.platform, arch: process.arch, version: process.versions.node
    })'"""
    output = run_captured(
        "Windows Node.js", [bash, "-c", command], cwd=root,
        environment=environment, timeout=30,
    )
    try:
        evidence = json.loads(output)
        require(isinstance(evidence, dict)
                and evidence.get("platform") == "win32" and evidence.get("arch") == "x64",
                "Windows x64 のネイティブNode.jsが必要です。")
        version = evidence.get("version", "")
        require(isinstance(version, str) and re.fullmatch(r"22\.\d+\.\d+", version),
                "Node.jsは22.xのパッチ版が必要です。")
        validate_node(version)
    except (TypeError, ValueError):
        raise GateError("Node.jsは22.22.2以上の22.xが必要です。") from None
    print(f"PASS: Windows x64 Node.js {version}", flush=True)


def validate_windows_archive(archive):
    validate_archive(archive)
    names = archive.namelist()
    require(WINDOWS_SCRIPTS <= set(names),
            "Windows配布ZIPにGit Bash用の必須スクリプトがありません。")
    # 同梱物の改行を直してから試験しない。配布時点で Bash用LFが保持されることを確認。
    require(all(b"\r\n" not in archive.read(name) for name in WINDOWS_SCRIPTS),
            "Windows配布ZIPのGit BashスクリプトがCRLFです。")
    # Windowsの一般的なファイルシステムでは大文字小文字のみの違いでは同名になる。
    require(len(names) == len({name.casefold() for name in names}),
            "Windows配布ZIPに名前の重複があります。")


def verify_tzdata(extracted, backend_python, environment):
    test_environment = dict(environment, PYTHONTZPATH="", PYTHONUTF8="1")
    output = run_captured(
        "tzdata", [backend_python, "-c", TOKYO_CHECK], cwd=extracted,
        environment=test_environment, timeout=30,
    )
    try:
        evidence = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        raise GateError("tzdata: 検証結果を取得できません。") from None
    require(isinstance(evidence, dict)
            and evidence.get("native_x64") is True and evidence.get("venv") is True
            and evidence.get("no_system_tzpath") is True
            and evidence.get("tokyo") == "2026-01-01T12:04:05+09:00",
            "tzdata: 新規Windows venvでAsia/Tokyo時刻変換を確認できません。")
    installed_version = evidence.get("tzdata", "")
    require(isinstance(installed_version, str)
            and re.fullmatch(r"[0-9][A-Za-z0-9_.+-]*", installed_version) is not None,
            "tzdata: 配布パッケージのバージョンを確認できません。")
    print(f"PASS: tzdata {installed_version}; PYTHONTZPATH 空 / Asia/Tokyo +09:00",
          flush=True)


def install_build_smoke(extracted, bash, environment):
    label = "Windows Git Bash setup-windows.sh"
    run_captured(label, [bash, "./devel/windows/setup-windows.sh"], cwd=extracted,
                 environment=environment, timeout=900)
    backend_python = extracted / "backend/.venv/Scripts/python.exe"
    require(backend_python.is_file()
            and (extracted / "frontend/node_modules/vite/bin/vite.js").is_file(),
            "新規展開先にWindows Python環境またはnpm依存がありません。")
    print(f"PASS: {label} / 空白を含む新規パス", flush=True)
    verify_tzdata(extracted, backend_python, environment)

    run_captured("Windows フロントエンドビルド", [bash, "-c", "npm run build"],
                 cwd=extracted / "frontend", environment=environment, timeout=240)
    require(all((extracted / "frontend/dist" / name).is_file()
                for name in ("index.html", "takeuchi-model.html")),
            "Windows配布版のビルドに必須2入口がありません。")
    print("PASS: Windows npm run build / Vite 2入口", flush=True)

    # 通常のdev-server-windows.shによる起動・停止・再起動は専用ヘルパーで検証。
    # ヘルパーは検証段階を安全な要約だけで表示する。必須ブラウザー未実行は非ゼロ。
    try:
        result = subprocess.run(
            [sys.executable, str(CI_DIR / "windows_server_smoke.py"),
             "--root", str(extracted), "--git-bash", str(bash),
             "--backend-python", str(backend_python)],
            cwd=extracted, env=environment, check=False, timeout=600,
        )
    except subprocess.TimeoutExpired:
        raise GateError("Windows実起動・再起動: タイムアウト") from None
    require(result.returncode == 0,
            f"Windows実起動・再起動・ブラウザー: 終了コード {result.returncode}")
    print("PASS: Windowsクリーン配布の全必須ゲート", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="#29配布候補のクリーンなチェックアウト")
    parser.add_argument("--git-bash", type=Path, help="Git for Windows bash.exeの絶対パス")
    args = parser.parse_args()
    require_native_windows()
    root = args.root.resolve(strict=True)
    require((root / "devel/package_release.py").is_file()
            and all((root / name.removeprefix("Caliboo/")).is_file()
                    for name in WINDOWS_SCRIPTS),
            "#29のWindows配布候補が必要です。")
    release = root / "release"
    require(not os.path.lexists(release),
            "release が既に存在します。クリーンな候補を指定してください。")
    environment = clean_environment()
    environment["PYTHONUTF8"] = "1"
    bash, msys_python = find_git_bash(args.git_bash, root, environment)
    environment["PYTHON"] = msys_python
    verify_node(root, bash, environment)
    print(f"Windows x64 / Python {platform.python_version()} / Git Bash 確認済み", flush=True)
    # !NOTE: Windows固有のパス処理を実際に通す。短いrunner temp直下に空白を含める。
    runner_temp = os.environ.get("RUNNER_TEMP")
    try:
        run_captured("Windows Git Bash build-windows.sh",
                     [bash, "./devel/windows/build-windows.sh"],
                     cwd=root, environment=environment, timeout=120)
        archives = list(release.glob("*_Caliboo.zip"))
        require(len(archives) == 1, "今回作成されたWindows ZIPが一意ではありません。")
        print("PASS: Windows Git Bash build-windows.sh", flush=True)
        with tempfile.TemporaryDirectory(prefix="caliboo windows zip ", dir=runner_temp) as temp:
            with zipfile.ZipFile(archives[0]) as archive:
                validate_windows_archive(archive)
                archive.extractall(temp)
            extracted = Path(temp) / "Caliboo"
            require(extracted.is_dir() and " " in str(extracted),
                    "空白を含む新規ディレクトリへの展開に失敗しました。")
            print("PASS: CRC / 配布構成 / Windows必須スクリプト / クリーン展開",
                  flush=True)
            install_build_smoke(extracted, bash, environment)
    finally:
        # 新規生成された配布ZIPのみローカルで後始末する。アップロードしない。
        if release.is_dir() and not release.is_symlink():
            for archive in release.glob("*_Caliboo.zip"):
                if archive.is_file():
                    archive.unlink()
            if not any(release.iterdir()):
                release.rmdir()


if __name__ == "__main__":
    try:
        main()
    except GateError as error:
        print(f"Windows配布ゲート失敗: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        # 例外値にはユーザー環境のパス等が含まれる。型名のみ出す。
        print(f"Windows配布ゲート失敗: {type(error).__name__}", file=sys.stderr)
        sys.exit(1)
