#!/usr/bin/env bash
# Windows + Git Bash 用。devel/ に配置。
# bash ./devel/build-windows.sh
# release/YYYYMMDD_Caliboo.zip にソース配布用 ZIP を作成（同日の ZIP は置換）。
# Python 3.12+ が必要。rsync / zip の追加インストールは不要。
# PYTHON は引数を含まないコマンド名または Python 実行ファイルパス。
set -euo pipefail
export PYTHONUTF8=1
die() { echo "ERROR: $*" >&2; exit 1; }
case "${1:-}" in
  -h|--help) sed -n '2,6p' "$0" | sed 's/^# //'; exit 0 ;;
  '') ;;
  *) die "引数は --help のみ指定できます。" ;;
esac
[[ $# -eq 0 ]] || die "引数が多すぎます。"
case "$(uname -s)" in MINGW*|MSYS*) ;; *) die "Windows の Git Bash から実行してください。" ;; esac
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(dirname -- "$script_dir")"
if [[ -n "${PYTHON:-}" ]]; then
  python_cmd=("$PYTHON")
elif [[ -f "$repo_root/backend/.venv/Scripts/python.exe" ]]; then
  python_cmd=("$repo_root/backend/.venv/Scripts/python.exe")
elif command -v py >/dev/null 2>&1 && py -3.12 -c 'import sys' >/dev/null 2>&1; then
  python_cmd=(py -3.12)
elif command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(sys.version_info < (3,12))' >/dev/null 2>&1; then
  python_cmd=(python)
elif command -v py >/dev/null 2>&1 && py -3 -c 'import sys' >/dev/null 2>&1; then
  python_cmd=(py -3)
else
  die "Python 3.12+ が見つかりません。"
fi
"${python_cmd[@]}" -c 'import sys; sys.exit(sys.platform != "win32" or sys.version_info < (3,12))' || die "Windows Python 3.12+ が必要です。"
"${python_cmd[@]}" -u - "$(cygpath -w "$repo_root")" <<'PY'
from datetime import datetime
from pathlib import Path
import fnmatch
import os
import sys
import tempfile
import zipfile

root = Path(sys.argv[1]).resolve()
app_name = "Caliboo"
excluded_dirs = {".temp", "node_modules", ".venv", "dist", "coverage", "__pycache__",
                 ".pytest_cache", "var", ".vscode", ".git"}
excluded_files = {".coverage", "tsconfig.tsbuildinfo", "settings.local.json",
                  "scheduled_tasks.lock", ".gitignore", ".editorconfig", "~BROMIUM"}
def excluded(name, is_dir):
    if name == "~BROMIUM":
        return True
    if is_dir:
        return name in excluded_dirs or fnmatch.fnmatchcase(name, "*.egg-info")
    return name in excluded_files or any(fnmatch.fnmatchcase(name, pattern) for pattern in
                                          ("*.pyc", "*.code-workspace", "*:Zone.Identifier"))

def check_link(path):
    if path.is_symlink() or path.is_junction():
        raise RuntimeError(f"リンクまたはジャンクションは同梱できません: {path}")

for name in ("backend", "frontend", "devel"):
    if not (root / name).is_dir():
        raise RuntimeError(f"必須フォルダーがありません: {root / name}")
release = root / "release"
release.mkdir(exist_ok=True)
check_link(release)
target = release / f"{datetime.now():%Y%m%d}_{app_name}.zip"
fd, temp_name = tempfile.mkstemp(prefix=".caliboo-", suffix=".zip", dir=release)
os.close(fd)
try:
    with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.mkdir(app_name + "/")
        def add_tree(source):
            check_link(source)
            archive.mkdir(f"{app_name}/{source.relative_to(root).as_posix()}/")
            for entry in sorted(source.iterdir(), key=lambda p: p.name):
                if excluded(entry.name, entry.is_dir()):
                    continue
                check_link(entry)
                if entry.is_dir():
                    add_tree(entry)
                elif entry.is_file():
                    archive.write(entry, f"{app_name}/{entry.relative_to(root).as_posix()}")
                else:
                    raise RuntimeError(f"通常ファイルではありません: {entry}")
        for name in ("backend", "frontend", "docs", "devel", ".devcontainer", ".claude"):
            source = root / name
            if source.exists():
                if not source.is_dir():
                    raise RuntimeError(f"フォルダーではありません: {source}")
                print(f"include: {name}")
                add_tree(source)
            else:
                print(f"skip: {name} (存在しません)")
        backlog = root / "BACKLOG.md"
        if backlog.exists():
            check_link(backlog)
            archive.write(backlog, f"{app_name}/BACKLOG.md")
        else:
            print("skip: BACKLOG.md (存在しません)")
    with zipfile.ZipFile(temp_name) as archive:
        bad_file = archive.testzip()
        if bad_file:
            raise RuntimeError(f"ZIP 検証に失敗しました: {bad_file}")
    os.replace(temp_name, target)
    print(f"package: {target}\ncomplete!")
finally:
    if os.path.exists(temp_name):
        os.unlink(temp_name)
PY
