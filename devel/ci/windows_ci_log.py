"""Windows CI's UTF-8 log and fixed stage diagnostics (no exception messages or values)."""

from pathlib import Path
import re
import sys


CI_DIR = Path(__file__).resolve().parent
CI_FILES = {"windows_package_gate.py", "windows_server_smoke.py", "package_gate.py",
            "browser_e2e.py", "windows_ci_log.py"}


def configure_utf8_stdio():
    # !NOTE: Git Bash/Actions redirects native Python's output; the code page can be non-UTF-8.
    # Set the real streams too, for local invocation without the workflow's startup environment.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


class StageLog:
    def __init__(self):
        self.stage = "startup"

    def begin(self, stage):
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", stage):
            raise ValueError("Invalid fixed stage")
        self.stage = stage
        print(f"START stage={stage}", flush=True)

    def failure(self, error):
        # !NOTE: This diagnostic never stringifies error, request data, args, or local variables.
        kind = type(error).__name__
        kind = kind if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", kind) else "unknown"
        cause = error.__cause__ or error.__context__
        cause_kind = type(cause).__name__ if cause is not None else ""
        cause_label = (f" cause={cause_kind}"
                       if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", cause_kind) else "")
        location = ""
        trace = error.__traceback__
        while trace is not None:
            file = Path(trace.tb_frame.f_code.co_filename)
            try:
                if file.name in CI_FILES and file.resolve().parent == CI_DIR:
                    location = f" source={file.name}:{trace.tb_lineno}"
            except (OSError, ValueError):
                pass
            trace = trace.tb_next
        print(f"FAIL stage={self.stage} exception={kind}{cause_label}{location}",
              file=sys.stderr, flush=True)
