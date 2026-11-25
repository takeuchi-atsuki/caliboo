"""Regression tests for rejecting empty and skipped required test suites."""

import ast
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import textwrap
from unittest.mock import patch

from postgres_diagnostics import (
    MIGRATION_STAGES, MIGRATION_TEST, REQUIRED_TESTS, TEST_FILE,
    business_stage, diagnostic_lines, execute_required_tests, migration_boundaries,
)

from quality_gate import (
    assert_pytest_results, assert_vitest_results, test_environment, validate_node,
)


class QualityGateTests(unittest.TestCase):
    def test_pytest_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tests.xml"
            path.write_text("<testsuites><testsuite><testcase/></testsuite></testsuites>")
            assert_pytest_results(path)

    def test_pytest_rejects_empty_skipped_failed_and_error(self):
        for body in ("", "<testcase><skipped/></testcase>", "<testcase><failure/></testcase>",
                     "<testcase><error/></testcase>"):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "tests.xml"
                path.write_text(f"<testsuites><testsuite>{body}</testsuite></testsuites>")
                with self.assertRaises(ValueError):
                    assert_pytest_results(path)

    def test_vitest_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tests.json"
            path.write_text(json.dumps(self.vitest_counts()))
            assert_vitest_results(path)

    def test_vitest_rejects_empty_skipped_failed_and_todo(self):
        for changes in (
            {"numTotalTests": 0, "numPassedTests": 0},
            {"numTotalTests": 2, "numPendingTests": 1},
            {"numTotalTests": 2, "numFailedTests": 1},
            {"numTotalTests": 2, "numTodoTests": 1},
        ):
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "tests.json"
                path.write_text(json.dumps(self.vitest_counts() | changes))
                with self.assertRaises(ValueError):
                    assert_vitest_results(path)

    def test_node_version(self):
        for version in ("v22.22.2", "22.23.4"):
            validate_node(version)
        for version in ("22.22.1", "22.4.0", "24.0.0"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                validate_node(version)

    def test_environment_does_not_inherit_service_or_test_options(self):
        with patch.dict(os.environ, {
            "CALIBOO_DATABASE_URL": "synthetic-placeholder",
            "OPENAI_API_KEY": "synthetic-placeholder",
            "PYTEST_ADDOPTS": "synthetic-placeholder",
            "VITE_EXTERNAL_URL": "synthetic-placeholder",
            "PATH": "synthetic-path",
        }, clear=True):
            self.assertEqual(test_environment(), {"PATH": "synthetic-path"})

    @staticmethod
    def vitest_counts():
        return dict(numTotalTests=1, numPassedTests=1, numFailedTests=0,
                    numPendingTests=0, numTodoTests=0)


class SafePostgresDiagnosticsTests(unittest.TestCase):
    # These are fabricated values, never data from a repository, server or user account.
    markers = ("synthetic-password-canary", "postgresql://synthetic.invalid/db",
               "synthetic-private-report-body")

    def run_fixture(self, failing_source):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = root / "backend"
            test_file = backend / "tests/postgresql/test_shared_db.py"
            test_file.parent.mkdir(parents=True)
            definitions = ["import pytest", "import sys", ""]
            for name in sorted(REQUIRED_TESTS):
                body = (failing_source if name == "test_migration_and_independent_sessions"
                        else "pass")
                definitions.append(f"def {name}():\n" + textwrap.indent(body, "    "))
            test_file.write_text("\n\n".join(definitions), encoding="utf-8")
            report = root / "test.xml"
            diagnostics = root / "diagnostics.json"
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith("PYTEST_")}
            public = StringIO()
            with redirect_stdout(public), redirect_stderr(public):
                returncode = execute_required_tests(backend, env, report, diagnostics)
                for line in diagnostic_lines(diagnostics):
                    print(line)
            return returncode, public.getvalue(), test_file.read_text(encoding="utf-8")

    def test_failure_diagnostic_is_static_and_does_not_expose_values(self):
        body = (
            f"print({self.markers[0]!r})\n"
            f"print({self.markers[1]!r}, file=sys.stderr)\n"
            "class SyntheticDbError(ValueError):\n"
            "    sqlstate = '23505'\n"
            "try:\n"
            f"    raise SyntheticDbError({self.markers[1]!r})\n"
            "except ValueError:\n"
            f"    assert False, {self.markers[2]!r}"
        )
        code, output, source = self.run_fixture(body)
        self.assertEqual(code, 1)
        self.assertIn("test_migration_and_independent_sessions phase=call outcome=failed", output)
        self.assertIn("test_migration_and_independent_sessions/assertion-01", output)
        self.assertIn("exception[1]=AssertionError", output)
        self.assertIn("exception[2]=SyntheticDbError sqlstate=23505", output)
        line = next(index for index, text in enumerate(source.splitlines(), 1)
                    if "assert False" in text)
        self.assertIn(f"backend/tests/postgresql/test_shared_db.py:{line}", output)
        for marker in self.markers:
            self.assertNotIn(marker, output)
        self.assertNotIn("assert False", output)

    def test_all_four_required_tests_pass_without_diagnostics(self):
        code, output, _source = self.run_fixture("pass")
        self.assertEqual(code, 0)
        self.assertEqual(output, "")

    def test_collection_error_never_publishes_raw_output(self):
        # An invalid synthetic test module can fail before any per-test report exists.
        code, output, _source = self.run_fixture(f"def invalid({self.markers[0]!r}):")
        self.assertNotEqual(code, 0)
        for marker in self.markers:
            self.assertNotIn(marker, output)

    def test_skipped_diagnostic_does_not_expose_reason(self):
        code, output, _source = self.run_fixture(f"pytest.skip({self.markers[0]!r})")
        self.assertEqual(code, 0)
        self.assertIn("phase=call outcome=skipped", output)
        self.assertNotIn(self.markers[0], output)

    def test_business_phases_from_static_candidate_structure(self):
        # The anchor structure mirrors the five normal workflow blocks, without app/DB access.
        source = textwrap.dedent("""
            def test_migration_and_independent_sessions():
                verify()
                with TestClient(app) as first:
                    login()
                    with session() as db:
                        questions = query()
                    check_progress()
                    other = TestClient(app)
                    verify_separate()
                with TestClient(app) as admin:
                    generate_proposal()
                    member = TestClient(app)
                    verify_restart()
                    assignment = create()
                    submit_and_feedback()
        """)
        boundaries = migration_boundaries(ast.parse(source))
        expected = {
            "verify()": MIGRATION_STAGES[0], "login()": MIGRATION_STAGES[1],
            "check_progress()": MIGRATION_STAGES[2],
            "verify_separate()": MIGRATION_STAGES[1],
            "generate_proposal()": MIGRATION_STAGES[3],
            "verify_restart()": MIGRATION_STAGES[1],
            "submit_and_feedback()": MIGRATION_STAGES[4],
        }
        for index, line in enumerate(source.splitlines(), 1):
            if line.strip() not in expected:
                continue
            chain = [{"frames": [{"path": TEST_FILE, "function": MIGRATION_TEST, "line": index}]}]
            self.assertEqual(business_stage(MIGRATION_TEST, chain, boundaries),
                             expected[line.strip()])
        self.assertEqual(migration_boundaries(ast.parse("def unrelated(): pass")), [])

    def test_unexpected_diagnostic_fields_are_not_rendered(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps([{
                "test": "test_migration_and_independent_sessions",
                "phase": "call", "outcome": "failed",
                "check": {"path": self.markers[1], "line": 2, "function": self.markers[0]},
                "exceptions": [{"type": self.markers[2], "sqlstate": self.markers[0],
                                "frames": []}],
                "private": list(self.markers),
            }]), encoding="utf-8")
            output = "\n".join(diagnostic_lines(path))
            self.assertIn("check=unlocated", output)
            self.assertIn("exception[1]=unknown", output)
            for marker in self.markers:
                self.assertNotIn(marker, output)


if __name__ == "__main__":
    unittest.main()
