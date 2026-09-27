#!/bin/bash
#
# ソースコード一式(node_modules等を含まない配布zip)を展開した直後に、
# バックエンド(Python)とフロントエンド(Node.js)の依存をインストールするスクリプト。
#
# 使い方:
#   bash ./devel/setup.sh            # 実行環境を自動判定
#   bash ./devel/setup.sh --venv     # backend/.venv を作成してそこへインストール
#   bash ./devel/setup.sh --system   # 現在の python3 環境へ直接インストール
#
# 環境変数:
#   PYTHON  使用するPythonコマンド(既定: python3)。例: PYTHON=python3.12
#
# !NOTE: 自動判定では、Dev Container内(/.dockerenv あり、または REMOTE_CONTAINERS=true)
#        なら --system、それ以外(ホストのWSL/Linux/macOS)なら --venv として扱う。
#        ホストのシステムPythonは PEP 668 により pip install が拒否されることが多いため。

set -euo pipefail

# ----------------------------------------
# パス解決
# ----------------------------------------

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(dirname "$script_dir")"
backend_dir="$repo_root/backend"
frontend_dir="$repo_root/frontend"
venv_dir="$backend_dir/.venv"

# ----------------------------------------
# 引数解析
# ----------------------------------------

install_mode="auto"
case "${1:-}" in
  "") ;;
  --venv) install_mode="venv" ;;
  --system) install_mode="system" ;;
  -h|--help)
    sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *)
    echo "ERROR: 不明な引数です: $1 (--venv / --system / --help)" >&2
    exit 1
    ;;
esac

if [ "$install_mode" = "auto" ]; then
  if [ -f /.dockerenv ] || [ "${REMOTE_CONTAINERS:-}" = "true" ]; then
    install_mode="system"
  else
    install_mode="venv"
  fi
fi

# ----------------------------------------
# 前提ツールの確認
# ----------------------------------------

python_cmd="${PYTHON:-python3}"

if ! command -v "$python_cmd" >/dev/null 2>&1; then
  echo "ERROR: $python_cmd が見つかりません。Python 3.12 以降をインストールしてください。" >&2
  exit 1
fi
if ! "$python_cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "ERROR: Python 3.12 以降が必要です(検出: $("$python_cmd" --version 2>&1))。" >&2
  echo "       別のPythonを使う場合は PYTHON=python3.12 のように指定してください。" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: node / npm が見つかりません。Node.js 22.4 以降をインストールしてください。" >&2
  exit 1
fi
# NOTE: frontendのtestスクリプトが指定する --no-experimental-webstorage は Node.js 22.4 で
#       追加されたフラグのため、それより古いNodeではテストが起動できない。
if ! node -e 'const [major, minor] = process.versions.node.split(".").map(Number);
              process.exit(major > 22 || (major === 22 && minor >= 4) ? 0 : 1)'; then
  echo "ERROR: Node.js 22.4 以降が必要です(検出: $(node --version))。" >&2
  exit 1
fi

echo "# environment"
echo "install mode : $install_mode"
echo "python       : $("$python_cmd" --version 2>&1) ($(command -v "$python_cmd"))"
echo "node         : $(node --version)"
echo "npm          : $(npm --version)"
echo

# ----------------------------------------
# バックエンド
# ----------------------------------------

echo "# backend"
if [ "$install_mode" = "venv" ]; then
  # NOTE: ensurepip が無い環境(Debian/Ubuntuで python3-venv 未導入)では venv 作成が
  #       pip を入れる前に失敗し、bin/python だけが残る。bin/python の有無ではなく
  #       pip が動くかで判定し、壊れた venv は --clear で作り直す。
  if ! "$venv_dir/bin/python" -m pip --version >/dev/null 2>&1; then
    if ! "$python_cmd" -m venv --clear "$venv_dir"; then
      echo "ERROR: venv を作成できませんでした。" >&2
      echo "       Debian/Ubuntu では sudo apt install python3-venv (または python3.12-venv) を実行してください。" >&2
      exit 1
    fi
  fi
  backend_python="$venv_dir/bin/python"
  "$backend_python" -m pip install --upgrade pip
else
  backend_python="$python_cmd"
fi

"$backend_python" -m pip install -e "$backend_dir[dev]"
echo

# ----------------------------------------
# フロントエンド
# ----------------------------------------

echo "# frontend"
# NOTE: package-lock.json と同じ版を再現するため npm install ではなく npm ci を使う。
(cd "$frontend_dir" && npm ci)
echo

# ----------------------------------------
# 完了
# ----------------------------------------

echo "setup complete!"
echo "開発サーバーの起動: bash ./devel/dev-server.sh"
echo "  frontend: http://localhost:5173/"
echo "  backend : http://localhost:8000/"
