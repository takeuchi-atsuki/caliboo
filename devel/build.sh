#!/bin/bash
# WSL / Linux / macOS 用。release/YYYYMMDD_Caliboo.zip を作成する。
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_cmd="${PYTHON:-python3}"
if ! "$python_cmd" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then
    echo "ERROR: Python 3.12 以降が必要です。PYTHON=python3.12 のように指定できます。" >&2
    exit 1
fi

exec "$python_cmd" "$script_dir/package_release.py" "$script_dir/.." "$@"
