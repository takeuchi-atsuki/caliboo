#!/usr/bin/env bash
# Windows + Git Bash 用。devel/setup-windows.sh に配置してください。
# bash ./devel/setup-windows.sh
# PYTHON='/c/path/to/python.exe' bash ./devel/setup-windows.sh
# Python 3.12+ / Node.js 22.4+ / npm が必要です。
set -euo pipefail

die() { echo "ERROR: $*" >&2; exit 1; }
case "${1:-}" in
  -h|--help) sed -n '2,5p' "$0" | sed 's/^# //'; exit 0 ;;
  ''|--venv) ;;
  *) die "引数は --venv または --help のみ指定できます。" ;;
esac
[[ $# -le 1 ]] || die "引数が多すぎます。"
case "$(uname -s)" in
  MINGW*|MSYS*) ;;
  *) die "Windows の Git Bash から実行してください。" ;;
esac
command -v cygpath >/dev/null 2>&1 || die "Git Bash の cygpath が見つかりません。"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(dirname -- "$script_dir")"
backend_dir="$repo_root/backend"
frontend_dir="$repo_root/frontend"
venv_dir="$backend_dir/.venv"
[[ -d "$backend_dir" && -d "$frontend_dir" ]] || die "devel/ に配置してください。親フォルダーに backend/ と frontend/ が必要です。"
[[ -f "$frontend_dir/package.json" ]] || die "frontend/package.json がありません。"
[[ -f "$frontend_dir/package-lock.json" || -f "$frontend_dir/npm-shrinkwrap.json" ]] || die "npm ci 用の lock ファイルがありません。"

# PYTHON は引数を含まない単一のコマンド名または実行ファイルのパス。
if [[ -n "${PYTHON:-}" ]]; then
  python_cmd=("$PYTHON")
elif command -v py >/dev/null 2>&1 && py -3.12 -c 'import sys' >/dev/null 2>&1; then
  python_cmd=(py -3.12)
elif command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(sys.version_info < (3, 12))' >/dev/null 2>&1; then
  python_cmd=(python)
elif command -v py >/dev/null 2>&1 && py -3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' >/dev/null 2>&1; then
  python_cmd=(py -3)
else
  die "Python 3.12 以降が見つかりません。インストール後 Git Bash を開き直してください。"
fi
"${python_cmd[@]}" -c 'import sys; sys.exit(sys.platform != "win32" or sys.version_info < (3, 12))' || die "Windows 版 Python 3.12 以降が必要です。"
command -v node >/dev/null 2>&1 || die "Node.js が見つかりません。"
command -v npm >/dev/null 2>&1 || die "npm が見つかりません。"
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(process.platform === "win32" && (a>22 || (a===22 && b>=4)) ? 0 : 1)' || die "Windows 版 Node.js 22.4 以降が必要です。"

backend_python="$venv_dir/Scripts/python.exe"
if [[ -e "$venv_dir" ]]; then
  "$backend_python" -c 'import sys; sys.exit(sys.platform != "win32" or sys.version_info < (3, 12) or sys.prefix == sys.base_prefix)' >/dev/null 2>&1 &&
    "$backend_python" -m pip --version >/dev/null 2>&1 ||
    die "既存の backend/.venv は利用できません。停止中のサーバーがないことを確認し、.venv を別名へ移動して再実行してください。"
else
  "${python_cmd[@]}" -m venv "$(cygpath -w "$venv_dir")"
fi

echo '# environment'
"$backend_python" --version
node --version
npm --version
echo '# backend'
"$backend_python" -m pip install --upgrade pip
"$backend_python" -m pip install -e "$(cygpath -w "$backend_dir")[dev]"
# Windows は IANA タイムゾーンDBを標準提供しないため、tzdata を追加。
"$backend_python" -m pip install tzdata
"$backend_python" -c 'from zoneinfo import ZoneInfo; print("timezone check:", ZoneInfo("Asia/Tokyo"))'
echo '# frontend'
(cd -- "$frontend_dir" && npm ci)
echo 'setup complete!'
echo 'VS Code の Python interpreter: backend/.venv/Scripts/python.exe'
echo '起動コマンドはアプリの README を確認してください。'
echo 'dev-server.sh が bin/python を参照している場合は Scripts/python.exe へ修正が必要です。'
