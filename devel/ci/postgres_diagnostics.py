"""Collect only static source locations and exception types from required PostgreSQL tests."""

import ast
import json
from pathlib import Path
import re
import subprocess
import sys
from traceback import walk_tb

import pytest


TEST_FILE = "tests/postgresql/test_shared_db.py"
REQUIRED_TESTS = {
    "test_ephemeral_seed_credentials_on_sqlite",
    "test_ephemeral_initial_admin_credentials_on_sqlite",
    "test_migration_and_independent_sessions",
    "test_separate_first_initialization_without_demo",
}
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,79}")
SOURCE = re.compile(
    r"tests/postgresql/test_shared_db\.py|src/caliboo_api(?:/[A-Za-z_][A-Za-z0-9_]*)+\.py"
)
MAX_EXCEPTIONS = 6
MAX_FRAMES = 8
MAX_RECORDS = 12
SQLSTATE = re.compile(r"[0-9A-Z]{5}")
MIGRATION_TEST = "test_migration_and_independent_sessions"
MIGRATION_STAGES = (
    "01-copy-sequences-verification",
    "02-login-independent-report",
    "03-parallel-quiz-progress",
    "04-assignment-proposal",
    "05-submission-feedback",
)
OTHER_STAGES = {
    "test_ephemeral_seed_credentials_on_sqlite": "sqlite-seed-control",
    "test_ephemeral_initial_admin_credentials_on_sqlite": "sqlite-admin-control",
    "test_separate_first_initialization_without_demo": "postgres-independent-initialization",
}
STAGES = {*MIGRATION_STAGES, *OTHER_STAGES.values(), "unlocated"}


def identifier(value, fallback="unknown"):
    return value if isinstance(value, str) and IDENTIFIER.fullmatch(value) else fallback


def location(backend, frame, lineno):
    try:
        relative = Path(frame.f_code.co_filename).resolve().relative_to(backend).as_posix()
    except (OSError, ValueError):
        return None
    if not SOURCE.fullmatch(relative):
        return None
    return {
        "path": relative,
        "line": lineno,
        "function": identifier(frame.f_code.co_name.strip("<>")),
    }


def exception_chain(backend, exception):
    """Never read exception messages, args, locals, assertion expressions or response bodies."""
    pending = [exception]
    seen = set()
    result = []
    while pending and len(result) < MAX_EXCEPTIONS:
        current = pending.pop(0)
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        frames = [
            point for frame, lineno in walk_tb(current.__traceback__)
            if (point := location(backend, frame, lineno)) is not None
        ]
        # Preserve the calling test and the innermost test helper even when app frames are numerous.
        test_frames = [point for point in frames if point["path"] == TEST_FILE]
        app_frames = [point for point in frames if point["path"] != TEST_FILE]
        selected = []
        for point in test_frames[:1] + test_frames[-2:]:
            if point not in selected:
                selected.append(point)
        selected.extend(app_frames[-(MAX_FRAMES - len(selected)):])
        state = getattr(current, "sqlstate", None)
        result.append({
            "type": identifier(type(current).__name__),
            "sqlstate": state if isinstance(state, str) and SQLSTATE.fullmatch(state) else None,
            "frames": selected,
        })
        pending.append(current.__cause__ or current.__context__)
        original = getattr(current, "orig", None)
        if isinstance(original, BaseException):
            pending.append(original)
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions[:MAX_EXCEPTIONS])
    return result


def assertion_number(tree, point):
    """Map a static assertion location to its ordinal, without publishing its expression."""
    if tree is None or point is None or point["path"] != TEST_FILE:
        return None
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if function.name != point["function"]:
            continue
        if not function.lineno <= point["line"] <= function.end_lineno:
            continue
        checks = sorted(
            (node for node in ast.walk(function) if isinstance(node, ast.Assert)),
            key=lambda node: (node.lineno, node.col_offset),
        )
        for number, check in enumerate(checks, 1):
            if check.lineno <= point["line"] <= check.end_lineno:
                return number
    return None


def assigned_names(node):
    if isinstance(node, ast.Assign):
        return {target.id for target in node.targets if isinstance(target, ast.Name)}
    return set()


def migration_boundaries(tree):
    """Locate the five static business phases by known AST checkpoints, not private values."""
    if tree is None:
        return []
    function = next((
        node for node in tree.body if isinstance(node, ast.FunctionDef)
        and node.name == MIGRATION_TEST
    ), None)
    if function is None:
        return []
    boundaries = [(function.lineno, MIGRATION_STAGES[0])]
    for node in ast.walk(function):
        if isinstance(node, ast.With):
            variables = {item.optional_vars.id for item in node.items
                         if isinstance(item.optional_vars, ast.Name)}
            if "first" in variables:
                boundaries.append((node.lineno, MIGRATION_STAGES[1]))
            if any("questions" in assigned_names(statement) for statement in node.body):
                boundaries.append((node.lineno, MIGRATION_STAGES[2]))
            if "admin" in variables:
                boundaries.append((node.lineno, MIGRATION_STAGES[3]))
        names = assigned_names(node)
        if names & {"other", "member"}:
            boundaries.append((node.lineno, MIGRATION_STAGES[1]))
        if "assignment" in names:
            boundaries.append((node.lineno, MIGRATION_STAGES[4]))
    # !NOTE: If the candidate changes its test structure, do not guess a business stage.
    if {stage for _, stage in boundaries} != set(MIGRATION_STAGES):
        return []
    return sorted(boundaries)


def business_stage(test, chain, boundaries):
    if test != MIGRATION_TEST:
        return OTHER_STAGES.get(test, "unlocated")
    # The outer test frame identifies the phase even if the actual failure is in a helper.
    for error in chain:
        for point in error["frames"]:
            if point["path"] == TEST_FILE and point["function"] == MIGRATION_TEST:
                preceding = [stage for line, stage in boundaries if line <= point["line"]]
                return preceding[-1] if preceding else "unlocated"
    return "unlocated"


class SafeDiagnostics:
    def __init__(self, backend, destination):
        self.backend = backend.resolve()
        self.destination = destination
        self.records = []
        try:
            self.tree = ast.parse((self.backend / TEST_FILE).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            self.tree = None
        self.boundaries = migration_boundaries(self.tree)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        if not (report.failed or report.skipped) or len(self.records) >= MAX_RECORDS:
            return
        chain = exception_chain(self.backend, call.excinfo.value) if call.excinfo else []
        check = next((
            points[-1] for error in chain
            if (points := [point for point in error["frames"] if point["path"] == TEST_FILE])
        ), None)
        self.records.append({
            "test": item.name if item.name in REQUIRED_TESTS else "unexpected_test",
            "phase": report.when,
            "outcome": "failed" if report.failed else "skipped",
            "stage": business_stage(item.name, chain, self.boundaries),
            "check": check,
            "assertion": assertion_number(self.tree, check),
            "exceptions": chain,
        })
        self.save()

    def save(self):
        self.destination.write_text(json.dumps(self.records), encoding="utf-8")

    def pytest_sessionfinish(self, session, exitstatus):
        self.save()


def valid_location(point):
    if not isinstance(point, dict):
        return False
    path = point.get("path")
    line = point.get("line")
    name = point.get("function")
    return (isinstance(path, str) and SOURCE.fullmatch(path) is not None
            and type(line) is int and 1 <= line <= 1_000_000
            and isinstance(name, str) and IDENTIFIER.fullmatch(name) is not None)


def diagnostic_lines(path):
    # Re-check every emitted field. Never echo unknown fields, raw JSON or report text.
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(records, list):
        return []
    lines = []
    for record in records[:MAX_RECORDS]:
        if not isinstance(record, dict):
            continue
        name = record.get("test")
        phase = record.get("phase")
        outcome = record.get("outcome")
        if not isinstance(name, str) or (name not in REQUIRED_TESTS and name != "unexpected_test"):
            continue
        if phase not in ("setup", "call", "teardown") or outcome not in ("failed", "skipped"):
            continue
        check = record.get("check")
        label = "unlocated"
        if valid_location(check) and check["path"] == TEST_FILE:
            number = record.get("assertion")
            suffix = (f"assertion-{number:02d}" if type(number) is int and 1 <= number <= 1000
                      else f"statement-L{check['line']}")
            label = f"{check['function']}/{suffix} (backend/{check['path']}:{check['line']})"
        stage = record.get("stage")
        if not isinstance(stage, str) or stage not in STAGES:
            stage = "unlocated"
        lines.append(f"PostgreSQL pytest: {name} phase={phase} outcome={outcome} "
                     f"stage={stage} check={label}")
        chain = record.get("exceptions")
        if not isinstance(chain, list):
            continue
        for index, error in enumerate(chain[:MAX_EXCEPTIONS], 1):
            if not isinstance(error, dict):
                continue
            name = identifier(error.get("type"))
            state = error.get("sqlstate")
            state_label = (f" sqlstate={state}" if isinstance(state, str)
                           and SQLSTATE.fullmatch(state) else "")
            lines.append(f"  exception[{index}]={name}{state_label}")
            frames = error.get("frames")
            if not isinstance(frames, list):
                continue
            for point in frames[:MAX_FRAMES]:
                if valid_location(point):
                    lines.append(f"    backend/{point['path']}:{point['line']} {point['function']}")
    return lines


def execute_required_tests(backend, environment, report, diagnostics):
    """Raw pytest stdout/stderr must never reach the public CI log, even on collection errors."""
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), str(report), str(diagnostics)],
            cwd=backend, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=False, timeout=300,
        )
    except subprocess.TimeoutExpired:
        return 124
    return result.returncode


def main():
    report, diagnostics = (Path(arg).resolve() for arg in sys.argv[1:])
    plugin = SafeDiagnostics(Path.cwd(), diagnostics)
    tests = [f"{TEST_FILE}::{name}" for name in sorted(REQUIRED_TESTS)]
    return pytest.main(
        ["--disable-socket", "-q", "--tb=no", "-p", "no:cacheprovider",
         f"--junitxml={report}", *tests],
        plugins=[plugin],
    )


if __name__ == "__main__":
    sys.exit(main())
