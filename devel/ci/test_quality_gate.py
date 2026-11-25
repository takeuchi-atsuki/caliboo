"""Regression tests for rejecting empty and skipped required test suites."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
