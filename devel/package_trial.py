"""限定Web試用向けの、履歴を持たない明示許可ソース一式を生成する。"""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile

MANIFEST = "devel/trial-source-allowlist.txt"
REQUIRED_FILES = {
    MANIFEST, "Dockerfile.trial", "Dockerfile.trial.dockerignore",
    "README.md", "CHANGELOG.md", "docs/trial-web.md", "backend/pyproject.toml",
    "backend/src/caliboo_api/main.py", "backend/src/caliboo_api/trial.py",
    "frontend/index.html", "frontend/package.json",
    "frontend/package-lock.json", "frontend/tsconfig.json", "frontend/vite.config.ts",
    "frontend/tailwind.config.ts", "frontend/src/main.tsx", "frontend/src/App.tsx",
}
FRONTEND_SUFFIXES = {".ts", ".tsx", ".css", ".svg", ".png", ".obj", ".mtl",
                     ".js", ".jsx", ".woff", ".woff2"}
SOURCE_ARCHIVE = "caliboo-trial-source.zip"


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], check=False,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if result.returncode:
        raise ValueError("指定されたGitスナップショットを取得できません。")
    return result.stdout


def parse_manifest(raw):
    paths = []
    for value in raw.decode("utf-8").splitlines():
        if not value or value.startswith("#"):
            continue
        path = PurePosixPath(value)
        if (path.as_posix() != value or path.is_absolute()
                or any(not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", part)
                       or part.lower() in {"public", "var", "logs", "trace", "traces",
                                           "secrets", "credentials", "__pycache__",
                                           "node_modules", "dist", "test", "tests"}
                       for part in path.parts)
                or ".spec." in path.name or ".test." in path.name):
            raise ValueError("試用ソース許可リストに配布対象外のパスがあります。")
        allowed_source = (
            (path.is_relative_to("backend/src/caliboo_api") and path.suffix in {".py", ".svg"})
            or (path.is_relative_to("frontend/src") and path.suffix in FRONTEND_SUFFIXES)
        )
        if value not in REQUIRED_FILES and not allowed_source:
            raise ValueError("試用ソース許可リストに配布対象外のパスがあります。")
        paths.append(value)
    if len(paths) != len(set(paths)) or not REQUIRED_FILES.issubset(paths):
        raise ValueError("試用ソース許可リストが不足または重複しています。")
    return sorted(paths)


def snapshot_entries(root, commit, paths):
    """許可パスがコミット上で通常ファイルか検証してからblob IDを返す。"""
    data = git(root, "ls-tree", "-r", "-z", "--full-tree", commit, "--", *paths)
    entries = {}
    for entry in data.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        path = name.decode("utf-8")
        if mode not in {"100644", "100755"} or kind != "blob" or path not in paths:
            raise ValueError("試用ソース許可リストに通常ファイル以外が含まれています。")
        entries[path] = oid
    if set(entries) != set(paths):
        raise ValueError("コミット上に必要な試用ソースがありません。")
    return entries


def create_package(root, ref, output):
    root = root.resolve(strict=True)
    if Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve() != root:
        raise ValueError("--root はリポジトリのルートを指定してください。")
    commit = git(root, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")
    commit = commit.decode("ascii").strip()
    # !NOTE: 作業ツリー自体は読み込まない。未コミットのDB、ログ、設定や
    #        ソース変更を誤って外部提供せず、検証対象のコミットに固定する。
    manifest = snapshot_entries(root, commit, [MANIFEST])[MANIFEST]
    paths = parse_manifest(git(root, "cat-file", "blob", manifest))
    entries = snapshot_entries(root, commit, paths)
    output = output.parent.resolve(strict=True) / output.name
    if output.exists() or output.is_symlink() or output.is_relative_to(root):
        raise ValueError("--output はチェックアウト外の新規パスを指定してください。")
    with tempfile.TemporaryDirectory(prefix=".caliboo-trial-", dir=output.parent) as temp:
        stage = Path(temp) / "deliverable"
        source = stage / "source"
        stage.mkdir(mode=0o700)
        source.mkdir()
        zip_path = stage / SOURCE_ARCHIVE
        with zipfile.ZipFile(zip_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in paths:
                content = git(root, "cat-file", "blob", entries[path])
                target = source / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                # 固定時刻で同じコミットから同じZIPを再生成できる。
                info = zipfile.ZipInfo(path)
                info.external_attr = 0o100644 << 16
                archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED)
        with zipfile.ZipFile(zip_path) as archive:
            if archive.namelist() != paths or archive.testzip() is not None:
                raise ValueError("試用ソースZIPの検証に失敗しました。")
        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        # 既存ディレクトリは上書きしない。公開物を置くのは全選別・検証の完了後。
        output.mkdir(mode=0o700)
        try:
            stage.replace(output)
        except OSError:
            output.rmdir()
            raise
    return commit, digest, len(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        commit, digest, count = create_package(args.root, args.ref, args.output)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"commit: {commit}")
    print(f"files: {count}")
    print(f"source: {args.output / 'source'}")
    print(f"zip: {args.output / SOURCE_ARCHIVE}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
