"""#29候補で配布ZIPを作成し、空ディレクトリへの展開から起動・再起動まで確認する。"""

import argparse
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[2]
CI_DIR = Path(__file__).resolve().parent
FORBIDDEN_COMPONENTS = {
    ".git", ".codex", ".agents", ".claude", "ssh_config", "node_modules", "dist", "var",
    "release", "coverage", "__pycache__", "public", "secrets", "credentials", "trace",
    "traces", "poc_takeuchi",
}
FORBIDDEN_DOCS = {
    "docs/poc-takeuchi-2026-09-29.md", "docs/poc-strength-profile-2026-09-29.md",
}


class GateError(RuntimeError):
    """安全な診断メッセージのみ表示するゲートのエラー。"""


def require(condition, message):
    if not condition:
        raise GateError(message)


def clean_environment():
    # !NOTE: 既存データの参照や外部AIの設定を引き継がず、初回ローカル構成を再現する。
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("CALIBOO_", "OPENAI_", "AZURE_OPENAI_"))
        and key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTEST_ADDOPTS"}
    }
    environment.update(CALIBOO_AI_PROVIDER="manual", CALIBOO_DEMO_SEED="false",
                       CALIBOO_COOKIE_SECURE="false", PYTHON=sys.executable)
    return environment


def run_package_regression(root, environment):
    # unittest の通常の終了コードではskipを成功扱いにするため、件数とskipも検査する。
    code = (
        "import unittest, sys; "
        "suite = unittest.defaultTestLoader.discover('devel', pattern='test_package_release.py'); "
        "expected = suite.countTestCases(); "
        "result = unittest.TextTestRunner(verbosity=2).run(suite); "
        "sys.exit(0 if expected >= 7 and result.testsRun == expected "
        "and result.wasSuccessful() and not result.skipped and not result.expectedFailures "
        "else 1)"
    )
    subprocess.run([sys.executable, "-c", code], cwd=root, env=environment,
                   check=True, timeout=90)


def validate_archive(archive):
    entries = archive.infolist()
    require(entries, "配布ZIPが空です。")
    names = set()
    for entry in entries:
        name = entry.filename
        path = PurePosixPath(name)
        prefix = path.parts[:1]
        require(prefix == ("Caliboo",) and not path.is_absolute()
                and ".." not in path.parts and "\\" not in name
                and name == path.as_posix(),
                "配布ZIPのルートまたはファイル名が不正です。")
        parts = path.parts[1:]
        lower = tuple(part.lower() for part in parts)
        require(not entry.is_dir() and not stat.S_ISLNK(entry.external_attr >> 16)
                and len(parts) > 0 and name not in names,
                "配布ZIPの重複・リンク・想定外のエントリがあります。")
        require(not any(
            part in FORBIDDEN_COMPONENTS or part.startswith(".env")
            or part in {"settings.local.json", "scheduled_tasks.lock"}
            or part.endswith((".db", ".sqlite", ".sqlite3", ".db-wal", ".sqlite-wal"))
            for part in lower
        ), "配布ZIPに開発専用または保存データ関連のパスがあります。")
        relative = "/".join(lower)
        require(relative not in FORBIDDEN_DOCS
                and not relative.startswith(("backend/tests/", "frontend/src/test/"))
                and ".test." not in lower[-1] and ".spec." not in lower[-1]
                and relative != "devel/test_package_release.py",
                "配布ZIPに開発テストまたは個人別PoCのパスがあります。")
        names.add(name)
    required_files = {
        "Caliboo/README.md", "Caliboo/CHANGELOG.md",
        "Caliboo/devel/setup.sh", "Caliboo/devel/dev-server.sh",
        "Caliboo/backend/pyproject.toml", "Caliboo/backend/src/caliboo_api/manage.py",
        "Caliboo/frontend/package.json", "Caliboo/frontend/package-lock.json",
    }
    require(required_files <= names, "配布ZIPに初回導入・起動の必須ファイルがありません。")
    require(archive.testzip() is None, "配布ZIPの読み戻し検査に失敗しました。")
    print(f"配布ZIP: {len(entries)} ファイル、同梱構成・読み戻し検査に成功", flush=True)


def clean_install_and_smoke(root, environment):
    # 利用者向け README と同じ setup.sh を実行し、新規venvと npm ci の両方を通す。
    subprocess.run(["bash", "./devel/setup.sh", "--venv"], cwd=root, env=environment,
                   check=True, timeout=600)
    backend_python = root / "backend/.venv/bin/python"
    require(backend_python.is_file(), "新規展開先にvenvが作成されませんでした。")
    require((root / "frontend/node_modules/.bin/vite").is_file(),
            "新規展開先にnpm依存が導入されませんでした。")
    subprocess.run(["npm", "run", "build"], cwd=root / "frontend", env=environment,
                   check=True, timeout=180)
    require(all((root / "frontend/dist" / name).is_file()
                for name in ("index.html", "takeuchi-model.html")),
            "配布版のViteビルドに必須2入口がありません。")
    subprocess.run(
        [sys.executable, str(CI_DIR / "browser_e2e.py"), "--root", str(root),
         "--backend-python", str(backend_python), "--require-initial-admin", "--distribution"],
        cwd=root, env=environment, check=True, timeout=180,
    )
    print("クリーン配布: 初回セットアップ・ビルド・ブラウザー通常操作・再起動に成功", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="配布候補のクリーンなチェックアウト")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    require((root / "devel/package_release.py").is_file()
            and (root / "devel/test_package_release.py").is_file(),
            "#29の配布候補が必要です。")
    release = root / "release"
    # 既存ユーザーのZIPを上書きしない。使い捨てチェックアウトで実行する。
    require(not os.path.lexists(release), "release が既に存在します。クリーンな候補を指定してください。")
    environment = clean_environment()
    run_package_regression(root, environment)
    with tempfile.TemporaryDirectory(prefix="caliboo-package-") as temp:
        archive_path = None
        try:
            subprocess.run(["bash", "./devel/build.sh"], cwd=root, env=environment,
                           check=True, timeout=120)
            archives = list(release.glob("*_Caliboo.zip"))
            require(len(archives) == 1, "今回作成されたZIPが一意ではありません。")
            archive_path = archives[0]
            with zipfile.ZipFile(archive_path) as archive:
                validate_archive(archive)
                archive.extractall(temp)
            extracted = Path(temp) / "Caliboo"
            require(extracted.is_dir(), "空ディレクトリへの展開に失敗しました。")
            clean_install_and_smoke(extracted, environment)
        finally:
            # 成功・失敗に関わらず今回生成された配布ZIPを送信/保存しない。
            if release.is_dir() and not release.is_symlink():
                for created_archive in release.glob("*_Caliboo.zip"):
                    if created_archive.is_file():
                        created_archive.unlink()
            if release.is_dir() and not any(release.iterdir()):
                release.rmdir()


if __name__ == "__main__":
    try:
        main()
    except GateError as error:
        print(f"配布ゲート失敗: {error}", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"配布ゲート失敗: {type(error).__name__}", file=sys.stderr)
        sys.exit(1)
