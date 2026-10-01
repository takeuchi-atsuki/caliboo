#!/usr/bin/env bash
# Windows + Git Bash 用。devel/ に配置。
# 先に bash ./devel/setup-windows.sh を実行してください。
# 起動: bash ./devel/dev-server-windows.sh / 停止: Ctrl+C
# PYTHON: 任意の Windows Python 実行ファイル（引数は含めない）。
set -euo pipefail
export PYTHONUTF8=1
die() { echo "ERROR: $*" >&2; exit 1; }
case "${1:-}" in
  -h|--help) sed -n '2,5p' "$0" | sed 's/^# //'; exit 0 ;;
  '') ;;
  *) die "引数は --help のみ指定できます。" ;;
esac
[[ $# -eq 0 ]] || die "引数が多すぎます。"
case "$(uname -s)" in MINGW*|MSYS*) ;; *) die "Windows の Git Bash から実行してください。" ;; esac
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(dirname -- "$script_dir")"
backend_python="${PYTHON:-$repo_root/backend/.venv/Scripts/python.exe}"
"$backend_python" -P -c 'import sys; sys.exit(sys.platform != "win32" or sys.version_info < (3,12))' || die "Windows Python 3.12+ が必要です。setup-windows.sh を実行してください。"
"$backend_python" -P -c 'import caliboo_api.main, uvicorn' || die "バックエンドを読み込めません。依存関係と上記エラーを確認してください。"
command -v node >/dev/null 2>&1 || die "Node.js が見つかりません。"
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(process.platform === "win32" && (a>22 || (a===22 && b>=4)) ? 0 : 1)' || die "Windows Node.js 22.4+ が必要です。"
[[ -d "$repo_root/backend/src" ]] || die "backend/src がありません。"
[[ -f "$repo_root/frontend/node_modules/vite/bin/vite.js" ]] || die "Vite がありません。setup-windows.sh を実行してください。"
node_exe="$(node -p 'process.execPath')"
# Windows Python に Windows 形式のパスを渡す。Vite は .cmd を経由せず直接起動。
exec "$backend_python" -u - "$(cygpath -w "$repo_root")" "$node_exe" <<'PY'
import ctypes
from ctypes import wintypes as w
from pathlib import Path
import signal
import subprocess
import sys
import time

# Job Object: supervisor 終了時に reload の子プロセスも残さない。
SIZE_T = ctypes.c_size_t
class BasicLimits(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong), ("LimitFlags", w.DWORD),
                ("MinimumWorkingSetSize", SIZE_T), ("MaximumWorkingSetSize", SIZE_T),
                ("ActiveProcessLimit", w.DWORD), ("Affinity", SIZE_T),
                ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]
class IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in
                ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                 "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]
class ExtendedLimits(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", BasicLimits), ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", SIZE_T), ("JobMemoryLimit", SIZE_T),
                ("PeakProcessMemoryUsed", SIZE_T), ("PeakJobMemoryUsed", SIZE_T)]
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
k.CreateJobObjectW.restype = w.HANDLE
k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
k.SetInformationJobObject.restype = w.BOOL
k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k.OpenProcess.restype = w.HANDLE
k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
k.AssignProcessToJobObject.restype = w.BOOL
k.CloseHandle.argtypes = [w.HANDLE]
k.CloseHandle.restype = w.BOOL
job = k.CreateJobObjectW(None, None)
if not job:
    raise ctypes.WinError(ctypes.get_last_error())
limits = ExtendedLimits()
limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
if not k.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
    error = ctypes.get_last_error()
    k.CloseHandle(job)
    raise ctypes.WinError(error)

root = Path(sys.argv[1])
processes = []
def interrupted(*_):
    raise KeyboardInterrupt
signal.signal(signal.SIGINT, interrupted)
signal.signal(signal.SIGTERM, interrupted)

def start(name, args, cwd):
    child = subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    processes.append((name, child))
    handle = k.OpenProcess(0x0100 | 0x0001, False, child.pid)  # SET_QUOTA | TERMINATE
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not k.AssignProcessToJobObject(job, handle):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        k.CloseHandle(handle)

status = 1
try:
    start("backend", [sys.executable, "-m", "uvicorn", "caliboo_api.main:app",
                      "--reload", "--reload-dir", "src", "--host", "127.0.0.1",
                      "--port", "8000"], root / "backend")
    start("frontend", [sys.argv[2], str(root / "frontend/node_modules/vite/bin/vite.js"),
                       "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
          root / "frontend")
    print("frontend: http://localhost:5173/\nbackend : http://localhost:8000/\n停止: Ctrl+C", flush=True)
    while True:
        for name, child in processes:
            code = child.poll()
            if code is not None:
                print(f"{name} が終了しました (exit={code})。両サーバーを停止します。", flush=True)
                status = code if 0 <= code <= 255 else 1
                raise SystemExit(status)
        time.sleep(0.25)
except KeyboardInterrupt:
    status = 130
except SystemExit as error:
    status = error.code
except Exception as error:
    print(f"ERROR: {error}", file=sys.stderr, flush=True)
finally:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    print("開発サーバーを停止しています...", flush=True)
    for _, child in processes:
        if child.poll() is None:
            try:
                child.send_signal(signal.CTRL_BREAK_EVENT)
            except OSError:
                pass
    deadline = time.monotonic() + 3
    while any(child.poll() is None for _, child in processes) and time.monotonic() < deadline:
        time.sleep(0.1)
    k.CloseHandle(job)  # 残った関連プロセスを終了
    for _, child in processes:
        if child.poll() is None:
            child.kill()  # Job 登録前のエラーにも対応
        child.wait()
sys.exit(status)
PY
