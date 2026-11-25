"""Windows配布ゲートの判定を合成入力で確認する（Windows実動とは別）。"""

from contextlib import redirect_stdout
from io import BytesIO, StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from windows_package_gate import (
    GateError, WINDOWS_SCRIPTS, find_git_bash, require_native_windows,
    run_captured, validate_windows_archive, verify_node, verify_tzdata,
)


BASE_FILES = {
    "Caliboo/README.md", "Caliboo/CHANGELOG.md",
    "Caliboo/devel/setup.sh", "Caliboo/devel/dev-server.sh",
    "Caliboo/backend/pyproject.toml", "Caliboo/backend/src/caliboo_api/manage.py",
    "Caliboo/frontend/package.json", "Caliboo/frontend/package-lock.json",
}


class WindowsPackageGateTests(unittest.TestCase):
    def archive(self, missing=(), additional=(), crlf=()):
        data = BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            for name in (BASE_FILES | WINDOWS_SCRIPTS | set(additional)) - set(missing):
                archive.writestr(name, "synthetic\r\n" if name in crlf else "synthetic\n")
        return zipfile.ZipFile(data)

    def test_archive_includes_three_lf_windows_entrypoints(self):
        with self.archive() as archive, redirect_stdout(StringIO()):
            validate_windows_archive(archive)

    def test_archive_rejects_missing_windows_entrypoint(self):
        for missing in WINDOWS_SCRIPTS:
            with self.subTest(missing=missing), self.archive(missing=[missing]) as archive:
                with redirect_stdout(StringIO()), self.assertRaises(GateError):
                    validate_windows_archive(archive)

    def test_archive_rejects_case_collision_and_crlf(self):
        for archive in (
            self.archive(additional=["Caliboo/docs/Usage.md", "Caliboo/docs/usage.md"]),
            self.archive(crlf=["Caliboo/devel/windows/setup-windows.sh"]),
        ):
            with archive, redirect_stdout(StringIO()), self.assertRaises(GateError):
                validate_windows_archive(archive)

    def test_tzdata_requires_venv_empty_tzpath_and_exact_known_conversion(self):
        fields = {
            "native_x64": True, "venv": True, "no_system_tzpath": True,
            "tokyo": "2026-01-01T12:04:05+09:00", "tzdata": "2026.1",
        }
        with patch("windows_package_gate.run_captured", return_value=json.dumps(fields)) as run:
            with redirect_stdout(StringIO()):
                verify_tzdata(Path("synthetic root"), Path("python.exe"), {"PATH": "synthetic"})
            self.assertEqual(run.call_args.kwargs["environment"]["PYTHONTZPATH"], "")
            self.assertEqual(run.call_args.kwargs["environment"]["PYTHONUTF8"], "1")
            self.assertEqual(run.call_args.kwargs["environment"]["PYTHONIOENCODING"], "utf-8")
        for changes in ({"native_x64": False}, {"venv": False}, {"no_system_tzpath": False},
                        {"tokyo": "2026-01-01T03:04:05+00:00"}, {"tzdata": ""}):
            with self.subTest(changes=changes), patch(
                "windows_package_gate.run_captured", return_value=json.dumps(fields | changes),
            ):
                with self.assertRaises(GateError):
                    verify_tzdata(Path("synthetic root"), Path("python.exe"), {})

    def test_native_node_validation(self):
        good = {"platform": "win32", "arch": "x64", "version": "22.23.4"}
        with patch("windows_package_gate.run_captured", return_value=json.dumps(good)):
            with redirect_stdout(StringIO()):
                verify_node(Path("synthetic root"), Path("bash.exe"), {})
        for changes in ({"platform": "linux"}, {"arch": "arm64"}, {"version": "22.22.1"},
                        {"version": "24.1.0"}):
            with self.subTest(changes=changes), patch(
                "windows_package_gate.run_captured", return_value=json.dumps(good | changes),
            ):
                with self.assertRaises(GateError):
                    verify_node(Path("synthetic root"), Path("bash.exe"), {})

    def test_stage_failure_redacts_raw_output(self):
        result = subprocess.CompletedProcess(
            args=["synthetic"], returncode=5,
            stdout="synthetic-private-stdout", stderr="synthetic-private-stderr",
        )
        with patch("windows_package_gate.subprocess.run", return_value=result):
            with self.assertRaises(GateError) as raised:
                run_captured("synthetic-stage", ["synthetic"], cwd=Path("."),
                             environment={}, timeout=1)
        self.assertIn("5", str(raised.exception))
        self.assertNotIn("synthetic-private", str(raised.exception))

    def test_git_bash_is_explicit_and_detected(self):
        with tempfile.TemporaryDirectory(prefix="synthetic path ") as directory:
            root = Path(directory)
            bash = root / "bash.exe"
            bash.touch()
            with patch("windows_package_gate.run_captured", return_value="/c/python.exe") as run:
                actual_bash, actual_python = find_git_bash(bash, root, {})
            self.assertEqual(actual_bash, bash.resolve())
            self.assertEqual(actual_python, "/c/python.exe")
            args = run.call_args.args[1]
            self.assertEqual(args[:2], [bash.resolve(), "-c"])
            self.assertIn("MINGW*|MSYS*", args[2])
            self.assertEqual(args[-1], sys.executable)

    def test_linux_is_not_windows_success(self):
        with patch("windows_package_gate.sys.platform", "linux"):
            with self.assertRaises(GateError):
                require_native_windows()


if __name__ == "__main__":
    unittest.main()
