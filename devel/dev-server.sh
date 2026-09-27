#!/bin/bash
#
# フロントエンド（Vite）とバックエンド（uvicorn）の開発サーバーを
# まとめて起動するスクリプト。
#
# 使い方:
#   bash ./devel/dev-server.sh   (初回は先に bash ./devel/setup.sh を実行する)
#   Ctrl+C で両サーバーを一括停止する。
#
# 環境変数:
#   PYTHON  バックエンドの起動に優先して使うPythonコマンド(setup.sh と同じ指定)

set -uo pipefail

# ----------------------------------------
# パス解決
# ----------------------------------------

script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(dirname "$script_dir")"

# ----------------------------------------
# 実行環境の選択・確認
# ----------------------------------------

# NOTE: devel/setup.sh は実行環境やオプションにより backend/.venv か現在の python3
#       (PYTHON 指定時はそのPython)へインストールする。候補を順に試し、
#       バックエンドを import できた最初のPythonを使う。
#       -P はカレントディレクトリを sys.path に入れず、未インストールの誤判定を防ぐ。
backend_python=""
import_errors=""
for candidate in ${PYTHON:+"$PYTHON"} "$repo_root/backend/.venv/bin/python" python3; do
  if ! command -v "$candidate" >/dev/null 2>&1; then
    continue
  fi
  if import_error="$("$candidate" -P -c 'import caliboo_api.main, uvicorn' 2>&1)"; then
    backend_python="$candidate"
    break
  fi
  import_errors+="  $candidate: $(printf '%s\n' "$import_error" | tail -n 1)"$'\n'
done

if [ -z "$backend_python" ]; then
  echo "ERROR: バックエンドを起動できるPythonが見つかりません。" >&2
  printf '%s' "$import_errors" >&2
  echo "先に bash ./devel/setup.sh を実行してください(PYTHON を指定してセットアップした場合は起動時も同じ PYTHON を指定する)。" >&2
  exit 1
fi
if [ ! -x "$repo_root/frontend/node_modules/.bin/vite" ]; then
  echo "ERROR: フロントエンドの依存が未インストールです。先に bash ./devel/setup.sh を実行してください。" >&2
  exit 1
fi

# ----------------------------------------
# 停止処理（Ctrl+C 等での一括クリーンアップ）
# ----------------------------------------

cleanup() {
  # NOTE: kill -TERM -- -$$ は自分自身のプロセスグループにもTERMを送るため、
  #       ガードなしだとINT/TERM/EXITトラップが連鎖してメッセージが複数回出力される。
  trap - INT TERM EXIT
  echo "開発サーバーを停止しています..."
  # NOTE: uvicorn --reload や Vite(node) は子プロセスを生成するため、個別PIDのkillでは残留する。
  kill -TERM -- -$$ 2>/dev/null
}
trap cleanup INT TERM EXIT

# ----------------------------------------
# サーバー起動
# ----------------------------------------

# NOTE: --reload-dir src で監視をソースに限定する(backend/.venv 等の変更でリロードさせないため)。
(cd "$repo_root/backend" && exec "$backend_python" -m uvicorn caliboo_api.main:app --reload --reload-dir src --port 8000) &
(cd "$repo_root/frontend" && exec ./node_modules/.bin/vite) &

# ----------------------------------------
# 終了待機
# ----------------------------------------

wait
