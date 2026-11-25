"""Windowsゲートの判定と所有プロセス停止方針の純粋な単体テスト。"""

from importlib.metadata import PackageNotFoundError
import io
import os
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import windows_server_smoke as smoke


class FakeBrowserError(Exception):
    pass


def fake_playwright():
    package = ModuleType("playwright")
    package.__path__ = []
    api = ModuleType("playwright.sync_api")
    api.Error = FakeBrowserError
    api.sync_playwright = Mock()
    playwright = api.sync_playwright.return_value.start.return_value
    browser = playwright.chromium.launch.return_value
    browser.version = "synthetic-version"
    modules = {"playwright": package, "playwright.sync_api": api,
               "browser_e2e": ModuleType("browser_e2e")}
    return modules, playwright, browser


class WindowsSmokeTest(unittest.TestCase):
    def setUp(self):
        # テスト用メッセージのみでも、CIの判定ログに混ぜない。
        self.stdout = patch("sys.stdout", new_callable=io.StringIO)
        self.stdout.start()
        self.addCleanup(self.stdout.stop)
        self.stderr = patch("sys.stderr", new_callable=io.StringIO)
        self.stderr.start()
        self.addCleanup(self.stderr.stop)

    def test_allowlist_drops_external_and_inherited_python(self):
        with patch.dict(os.environ, {
            "CALIBOO_DATABASE_URL": "synthetic", "CALIBOO_SQLITE_PATH": "synthetic",
            "OPENAI_API_KEY": "synthetic", "PYTHON": "synthetic", "HTTP_PROXY": "synthetic",
        }):
            result = smoke.clean_environment()
        for name in ("CALIBOO_DATABASE_URL", "CALIBOO_SQLITE_PATH", "OPENAI_API_KEY", "PYTHON",
                     "HTTP_PROXY"):
            self.assertNotIn(name, result)
        self.assertEqual(result["CALIBOO_DEMO_SEED"], "false")
        self.assertEqual(result["CALIBOO_AI_PROVIDER"], "manual")
        self.assertEqual(result["PYTHONUTF8"], "1")
        self.assertEqual(result["PYTHONIOENCODING"], "utf-8")

    def test_missing_playwright_is_only_unavailable(self):
        server = Mock()
        with patch.object(smoke, "version", side_effect=PackageNotFoundError("playwright")):
            self.assertFalse(smoke.run_ui_if_available(server, {}, "synthetic", "synthetic"))
        server.assert_not_called()

    def test_wrong_playwright_is_only_unavailable(self):
        server = Mock()
        with patch.object(smoke, "version", return_value="different-version"):
            self.assertFalse(smoke.run_ui_if_available(server, {}, "synthetic", "synthetic"))
        server.assert_not_called()

    def test_unavailable_sandbox_fails_closed(self):
        server = Mock()
        modules, playwright, _browser = fake_playwright()
        playwright.chromium.launch.side_effect = FakeBrowserError("sandbox unavailable")
        with patch.dict(sys.modules, modules), patch.object(
            smoke, "version", return_value=smoke.PLAYWRIGHT_VERSION
        ):
            self.assertFalse(smoke.run_ui_if_available(server, {}, "synthetic", "synthetic"))
        playwright.chromium.launch.assert_called_once_with(chromium_sandbox=True, env={})
        playwright.stop.assert_called_once()
        server.assert_not_called()

    def test_assertion_after_browser_launch_is_not_treated_as_unavailable(self):
        modules, playwright, browser = fake_playwright()
        server = Mock(side_effect=AssertionError("synthetic UI failure"))
        with patch.dict(sys.modules, modules), patch.object(
            smoke, "version", return_value=smoke.PLAYWRIGHT_VERSION
        ):
            with self.assertRaises(AssertionError):
                smoke.run_ui_if_available(server, {}, "synthetic", "synthetic")
        server.assert_called_once()
        browser.close.assert_called_once()
        playwright.stop.assert_called_once()

    def test_termination_tries_control_event_without_force(self):
        process = Mock()
        process.poll.side_effect = [None, 0]
        with patch.object(smoke.signal, "CTRL_BREAK_EVENT", 1, create=True), patch.object(
            smoke.subprocess, "run"
        ) as run, patch.object(smoke, "wait_ports_released") as release:
            smoke.terminate_owned_tree(process, {})
        process.send_signal.assert_called_once_with(1)
        run.assert_not_called()
        release.assert_called_once()

    def test_termination_force_fallback_targets_only_owned_pid_tree(self):
        process = Mock(pid=12345)
        process.poll.side_effect = [None, None]
        process.send_signal.side_effect = OSError("synthetic no console")
        env = {"SystemRoot": "synthetic-system-path"}
        with patch.object(smoke.signal, "CTRL_BREAK_EVENT", 1, create=True), patch.object(
            smoke.subprocess, "run", return_value=SimpleNamespace(returncode=0)
        ) as run, patch.object(smoke, "wait_ports_released") as release:
            smoke.terminate_owned_tree(process, env)
        self.assertEqual(run.call_args.args[0][1:], ["/PID", "12345", "/T", "/F"])
        release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
