"""Run the existing Caliboo quality entry points and require nonempty test results."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]


def assert_pytest_results(path: Path) -> None:
    """Pytest exit code alone does not distinguish skips from passes."""
    cases = ET.parse(path).getroot().findall(".//testcase")
    if not cases or any(
        case.find(tag) is not None
        for case in cases
        for tag in ("skipped", "failure", "error")
    ):
        raise ValueError("Required pytest suite must contain passing tests only")
    print(f"Required pytest tests passed: {len(cases)}", flush=True)


def assert_vitest_results(path: Path) -> None:
    result = json.loads(path.read_text(encoding="utf-8"))
    total = result["numTotalTests"]
    if (
        not isinstance(total, int)
        or total <= 0
        or result["numPassedTests"] != total
        or result["numFailedTests"] != 0
        or result["numPendingTests"] != 0
        or result["numTodoTests"] != 0
    ):
        raise ValueError("Required Vitest suite must contain passing tests only")
    print(f"Required Vitest tests passed: {total}", flush=True)


def validate_node(version: str) -> None:
    major, minor, patch = map(int, version.removeprefix("v").split("."))
    if major != 22 or (minor, patch) < (22, 2):
        raise ValueError("This quality gate requires Node.js 22.22.2 or later in the 22.x line")


def test_environment() -> dict[str, str]:
    # !NOTE: Local invocations must not inherit an actual DB/API configuration or
    # pytest options that could deselect required test cases.
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("CALIBOO_", "OPENAI_", "AZURE_OPENAI_", "PYTEST_", "PG", "VITE_"))
        and key not in {"DATABASE_URL", "NODE_OPTIONS"}
    }


def run(*args: str, cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(args, cwd=cwd, env=env, check=True)


def backend() -> None:
    if sys.version_info[:2] != (3, 12):
        raise ValueError("This quality gate requires Python 3.12")
    cwd = ROOT / "backend"
    with tempfile.TemporaryDirectory(prefix="caliboo-ci-") as directory:
        env = test_environment()
        env.update(
            CALIBOO_SQLITE_PATH=str(Path(directory) / "fallback.db"),
            CALIBOO_DEMO_SEED="true",
            CALIBOO_AI_PROVIDER="manual",
            CALIBOO_COOKIE_SECURE="false",
        )
        run(sys.executable, "-m", "flake8", "src", "tests", cwd=cwd, env=env)
        unit = Path(directory) / "unit.xml"
        integration = Path(directory) / "integration.xml"
        run(
            sys.executable, "-m", "pytest", "--disable-socket", "tests/unit/",
            "--cov=caliboo_api", "--cov-report=term-missing", "--cov-fail-under=95",
            f"--junitxml={unit}", cwd=cwd, env=env,
        )
        assert_pytest_results(unit)
        run(
            sys.executable, "-m", "pytest", "--disable-socket", "tests/integration/",
            f"--junitxml={integration}", cwd=cwd, env=env,
        )
        assert_pytest_results(integration)


def frontend() -> None:
    cwd = ROOT / "frontend"
    env = test_environment()
    validate_node(subprocess.check_output(["node", "--version"], env=env, text=True).strip())
    run("npm", "run", "lint", cwd=cwd, env=env)
    with tempfile.TemporaryDirectory(prefix="caliboo-ci-") as directory:
        report = Path(directory) / "vitest.json"
        run(
            "npm", "run", "test:coverage", "--", "--reporter=default",
            "--reporter=json", f"--outputFile.json={report}", cwd=cwd, env=env,
        )
        assert_vitest_results(report)
    run("npm", "run", "build", cwd=cwd, env=env)
    for entry in ("index.html", "takeuchi-model.html"):
        output = cwd / "dist" / entry
        if not output.is_file() or output.stat().st_size == 0:
            raise ValueError(f"Required Vite entry missing: dist/{entry}")
    print("Both Vite HTML entries built", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gate", choices=("backend", "frontend"))
    args = parser.parse_args()
    {"backend": backend, "frontend": frontend}[args.gate]()


if __name__ == "__main__":
    main()
