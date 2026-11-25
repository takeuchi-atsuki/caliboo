"""ローカルPoC用のソース配布ZIPを生成する。"""

import argparse
from datetime import datetime
import os
from pathlib import Path
import stat
import sys
import tempfile
import zipfile


APP_NAME = "Caliboo"
REQUIRED_FILES = (
    "README.md",
    "CHANGELOG.md",
    "backend/pyproject.toml",
    "backend/src/caliboo_api/__init__.py",
    "backend/src/caliboo_api/main.py",
    "backend/src/caliboo_api/config.py",
    "backend/src/caliboo_api/db.py",
    "backend/src/caliboo_api/models.py",
    "frontend/index.html",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/takeuchi-model.html",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    "frontend/tailwind.config.ts",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
    "devel/README.md",
    "devel/build.sh",
    "devel/package_release.py",
    "devel/setup.sh",
    "devel/dev-server.sh",
)
OPTIONAL_FILES = (
    "AGENTS.md",
    "BACKLOG.md",
    "devel/windows/build-windows.sh",
    "devel/windows/setup-windows.sh",
    "devel/windows/dev-server-windows.sh",
    ".devcontainer/Dockerfile",
    ".devcontainer/devcontainer.json",
    ".devcontainer/devcontainer-lock.json",
    ".devcontainer/openssl-x25519.cnf",
    ".devcontainer/requirements.txt",
    ".devcontainer/requirements-dev.txt",
    ".devcontainer/setup.sh",
    ".devcontainer/startup.sh",
)
# !NOTE: 実データを含むPoCの記録や開発AIの設定は配布対象にしない。
#        backend/、frontend/、devel/全体を再帰的にコピーする方式を避ける。
SOURCE_TREES = (
    ("backend/src", {".py", ".svg"}, True),
    ("frontend/src", {
        ".ts", ".tsx", ".js", ".jsx", ".css", ".scss", ".svg", ".png",
        ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".woff", ".woff2",
        ".obj", ".mtl", ".html",
    }, True),
    ("docs", {".md"}, False),
)
EXCLUDED_NAMES = {
    "var", "node_modules", "dist", "build", "coverage", "__pycache__",
    "release", "tmp", "temp", "scratch", "artifacts", "logs", "trace", "traces", "public",
    "secrets", "credentials", "settings.local.json", "scheduled_tasks.lock",
    "ssh_config", "~bromium",
}
EXCLUDED_DOCS = {
    "docs/poc-takeuchi-2026-09-29.md",
    "docs/poc-strength-profile-2026-09-29.md",
}


def excluded(path, root):
    """再帰対象内でも、既知の作業用・秘密ファイル名は先に除外する。"""
    name = path.name.lower()
    relative = path.relative_to(root)
    # !NOTE: 開発テストは完全チェックアウトで実施する。一部が配布対象外の
    #        .codexを参照するため、欠けたテスト一式をZIPに同梱しない。
    if relative.is_relative_to("frontend/src"):
        if relative.is_relative_to("frontend/src/test"):
            return True
        if ".spec." in name or ".test." in name:
            return True
    return (
        name.startswith(".")
        or name in EXCLUDED_NAMES
        or name.endswith((".egg-info", ".tsbuildinfo", ".local", ".bak", ".tmp", "~"))
        or ".local." in name
        or name.startswith(("secret.", "secrets.", "credential.", "credentials."))
        or relative.as_posix() in EXCLUDED_DOCS
    )


def checked_mode(path, root):
    """配布元の外へ出るリンクや特殊ファイルを拒否する。"""
    for entry in (path, *path.parents):
        if entry == root:
            break
        mode = entry.lstat().st_mode
        if stat.S_ISLNK(mode) or entry.is_junction():
            raise ValueError(f"リンクまたはジャンクションは同梱できません: {entry}")
    return path.lstat().st_mode


def checked_file(path, root):
    if not stat.S_ISREG(checked_mode(path, root)):
        raise ValueError(f"通常ファイルではありません: {path}")
    return path


def iter_source_files(directory, root, suffixes):
    if not stat.S_ISDIR(checked_mode(directory, root)):
        raise ValueError(f"フォルダーではありません: {directory}")
    for path in sorted(directory.iterdir()):
        if excluded(path, root):
            continue
        mode = checked_mode(path, root)
        if stat.S_ISDIR(mode):
            yield from iter_source_files(path, root, suffixes)
        elif stat.S_ISREG(mode):
            if path.suffix.lower() in suffixes:
                yield path
        else:
            raise ValueError(f"通常ファイルではありません: {path}")


def collect_files(root):
    paths = set()
    for relative in REQUIRED_FILES:
        path = root / relative
        if not os.path.lexists(path):
            raise FileNotFoundError(f"必須ファイルがありません: {path}")
        paths.add(checked_file(path, root))
    for relative in OPTIONAL_FILES:
        path = root / relative
        if os.path.lexists(path):
            paths.add(checked_file(path, root))
    for relative, suffixes, required in SOURCE_TREES:
        path = root / relative
        if os.path.lexists(path):
            paths.update(iter_source_files(path, root, suffixes))
        elif required:
            raise FileNotFoundError(f"必須フォルダーがありません: {path}")
    return sorted(paths)


def create_package(root):
    root = root.resolve()
    paths = collect_files(root)
    release_dir = root / "release"
    release_dir.mkdir(exist_ok=True)
    if not stat.S_ISDIR(checked_mode(release_dir, root)):
        raise ValueError(f"フォルダーではありません: {release_dir}")
    target = release_dir / f"{datetime.now():%Y%m%d}_{APP_NAME}.zip"

    # !NOTE: 同じファイルシステム上に新しいZIPを作り、読み戻しに成功した
    #        場合のみ置換する。途中失敗しても既存の正常なZIPには触れない。
    fd, name = tempfile.mkstemp(prefix=".caliboo-", suffix=".zip", dir=release_dir)
    temp = Path(name)
    try:
        os.close(fd)
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in paths:
                checked_file(path, root)
                archive.write(path, f"{APP_NAME}/{path.relative_to(root).as_posix()}")
        with zipfile.ZipFile(temp) as archive:
            bad_file = archive.testzip()
            if bad_file is not None:
                raise ValueError(f"ZIPの検証に失敗しました: {bad_file}")
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        target = create_package(args.root)
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"package: {target}")
    print("complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
