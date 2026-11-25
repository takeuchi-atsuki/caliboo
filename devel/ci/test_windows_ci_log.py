"""Regression coverage for redirected Windows code pages and safe CI diagnostics."""

from io import BytesIO, StringIO, TextIOWrapper
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from windows_ci_log import StageLog, configure_utf8_stdio


class WindowsCiLogTests(unittest.TestCase):
    def test_legacy_codepage_reproduces_error_then_utf8_prints_both_streams(self):
        output = BytesIO()
        errors = BytesIO()
        stdout = TextIOWrapper(output, encoding="cp1252")
        stderr = TextIOWrapper(errors, encoding="cp1252")
        with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
            with self.assertRaises(UnicodeEncodeError):
                print("Git Bash 確認済み", flush=True)
            configure_utf8_stdio()
            print("Git Bash 確認済み", flush=True)
            print("日本語の診断", file=sys.stderr, flush=True)
        self.assertEqual(stdout.encoding, "utf-8")
        self.assertEqual(stderr.encoding, "utf-8")
        self.assertIn("確認済み", output.getvalue().decode("utf-8"))
        self.assertIn("日本語の診断", errors.getvalue().decode("utf-8"))

    def test_stage_error_uses_only_safe_exception_metadata(self):
        output = StringIO()
        errors = StringIO()
        with patch.object(sys, "stdout", output), patch.object(sys, "stderr", errors):
            configure_utf8_stdio()
            log = StageLog()
            log.begin("build-zip")
            try:
                try:
                    raise UnicodeEncodeError("cp1252", "synthetic-private-text", 0, 1,
                                             "synthetic-private-reason")
                except UnicodeEncodeError as cause:
                    raise RuntimeError("synthetic-private-value") from cause
            except RuntimeError as error:
                log.failure(error)
        self.assertEqual(output.getvalue().strip(), "START stage=build-zip")
        self.assertIn("FAIL stage=build-zip exception=RuntimeError cause=UnicodeEncodeError",
                      errors.getvalue())
        self.assertNotIn("synthetic-private", errors.getvalue())

    def test_both_real_cli_entrypoints_print_help_as_utf8_with_legacy_env(self):
        env = dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="cp1252")
        for script in ("windows_package_gate.py", "windows_server_smoke.py"):
            with self.subTest(script=script):
                path = Path(__file__).resolve().parent / script
                result = subprocess.run([sys.executable, str(path), "--help"], env=env,
                                        capture_output=True, check=False, timeout=30)
                self.assertEqual(result.returncode, 0)
                self.assertIn("Windows", result.stdout.decode("utf-8"))
                self.assertNotIn(b"UnicodeEncodeError", result.stderr)


if __name__ == "__main__":
    unittest.main()
