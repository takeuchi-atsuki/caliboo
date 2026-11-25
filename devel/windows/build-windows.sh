#!/usr/bin/env bash
# Windows + Git Bash 用。
# bash ./devel/windows/build-windows.sh
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
# 旧手順でdevel/にコピーした場合と、リポジトリのwindows/配置の両方に対応。
devel_dir="$script_dir"
if [[ "$(basename -- "$script_dir")" == windows ]]; then
  devel_dir="$(dirname -- "$script_dir")"
fi
repo_root="$(dirname -- "$devel_dir")"
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
exec "${python_cmd[@]}" -u "$(cygpath -w "$devel_dir/package_release.py")" "$(cygpath -w "$repo_root")"
