"""coverage_include_warning フックの公開契約準拠テスト。外部接続不要。

main()(stdin の JSON → 対象パスかつcoverage.include未列挙ならexit code 2でstderrへ
警告 / それ以外は何も出力せず正常終了)の入出力仕様を検証する。

`.codex/hooks/`はpythonpath外かつ非パッケージのため、
importlib.util.spec_from_file_locationでモジュールをロードする
。
"""

import importlib.util
import io
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

_HOOK_PATH = Path(__file__).parent / "coverage_include_warning.py"


def _load_hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("coverage_include_warning", _HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coverage_include_warning = _load_hook()


def _make_repo(tmp_path: Path, include_lines: list[str]) -> Path:
    """`frontend/vite.config.ts`を持つ最小のリポジトリルートを用意する。"""
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    include_body = ",\n".join(f'      "{line}"' for line in include_lines)
    (frontend / "vite.config.ts").write_text(
        "export default {\n  test: {\n    coverage: {\n"
        f"      include: [\n{include_body}\n      ],\n"
        "    },\n  },\n}};\n",
        encoding="utf-8",
    )
    return tmp_path


def _write_target_file(repo_root: Path, relative_path: str) -> str:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("export {};\n", encoding="utf-8")
    return str(path)


def _run_main(monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    coverage_include_warning.main()


def _run_main_raw_stdin(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(raw))
    coverage_include_warning.main()


class TestWarnsOnUnlistedTargetPath:
    def test_lib_ts_not_listed_emits_warning_and_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repo_root = _make_repo(tmp_path, ["src/lib/apiClient.ts"])
        file_path = _write_target_file(repo_root, "frontend/src/lib/newClient.ts")

        with pytest.raises(SystemExit) as exc_info:
            _run_main(
                monkeypatch,
                {"tool_input": {"file_path": file_path}, "cwd": str(repo_root)},
            )

        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "frontend/src/lib/newClient.ts" in err
        assert "coverage.include" in err

    def test_features_use_hook_not_listed_emits_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repo_root = _make_repo(tmp_path, [])
        file_path = _write_target_file(
            repo_root, "frontend/src/features/home/useHomeSummary.ts"
        )

        with pytest.raises(SystemExit) as exc_info:
            _run_main(
                monkeypatch,
                {"tool_input": {"file_path": file_path}, "cwd": str(repo_root)},
            )

        assert exc_info.value.code == 2


class TestSilentWhenListedOrOutOfScope:
    def test_listed_path_emits_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repo_root = _make_repo(tmp_path, ["src/lib/apiClient.ts"])
        file_path = _write_target_file(repo_root, "frontend/src/lib/apiClient.ts")

        _run_main(monkeypatch, {"tool_input": {"file_path": file_path}, "cwd": str(repo_root)})

        assert capsys.readouterr().err == ""

    def test_component_page_path_is_out_of_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repo_root = _make_repo(tmp_path, [])
        file_path = _write_target_file(
            repo_root, "frontend/src/features/home/HomePage.tsx"
        )

        _run_main(monkeypatch, {"tool_input": {"file_path": file_path}, "cwd": str(repo_root)})

        assert capsys.readouterr().err == ""

    def test_backend_path_is_out_of_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        repo_root = _make_repo(tmp_path, [])
        file_path = _write_target_file(repo_root, "backend/src/caliboo_api/main.py")

        _run_main(monkeypatch, {"tool_input": {"file_path": file_path}, "cwd": str(repo_root)})

        assert capsys.readouterr().err == ""

    def test_lib_subdirectory_ts_is_out_of_scope(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """パターンは`src/lib/*.ts`(直下)のみを対象にし、サブディレクトリは対象外。"""
        repo_root = _make_repo(tmp_path, [])
        file_path = _write_target_file(repo_root, "frontend/src/lib/sub/nested.ts")

        _run_main(monkeypatch, {"tool_input": {"file_path": file_path}, "cwd": str(repo_root)})

        assert capsys.readouterr().err == ""


class TestFailOpenOnInvalidInput:
    def test_missing_file_path_no_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _run_main(monkeypatch, {"tool_input": {}, "cwd": "/workspaces/caliboo"})
        assert capsys.readouterr().err == ""

    def test_missing_cwd_no_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        file_path = _write_target_file(tmp_path, "frontend/src/lib/newClient.ts")
        _run_main(monkeypatch, {"tool_input": {"file_path": file_path}})
        assert capsys.readouterr().err == ""

    def test_non_json_stdin_no_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _run_main_raw_stdin(monkeypatch, "not json")
        assert capsys.readouterr().err == ""

    def test_non_dict_top_level_stdin_no_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _run_main_raw_stdin(monkeypatch, "[]")
        assert capsys.readouterr().err == ""

    def test_file_path_outside_cwd_no_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        other_root = tmp_path / "elsewhere"
        file_path = _write_target_file(other_root, "frontend/src/lib/newClient.ts")
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        _run_main(monkeypatch, {"tool_input": {"file_path": file_path}, "cwd": str(repo_root)})

        assert capsys.readouterr().err == ""

    def test_missing_vite_config_no_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """vite.config.tsが読めない場合は判定不能として警告しない(fail-open)。"""
        (tmp_path / "frontend").mkdir()
        file_path = _write_target_file(tmp_path, "frontend/src/lib/newClient.ts")

        _run_main(monkeypatch, {"tool_input": {"file_path": file_path}, "cwd": str(tmp_path)})

        assert capsys.readouterr().err == ""


class TestCodexPatch:
    def test_multiple_files_from_frontend_cwd(self, tmp_path, monkeypatch, capsys):
        repo_root = _make_repo(tmp_path, ["src/lib/apiClient.ts"])
        for name in ("apiClient.ts", "newClient.ts", "otherClient.ts"):
            _write_target_file(repo_root, f"frontend/src/lib/{name}")
        patch = "\n".join([
            "*** Begin Patch",
            "*** Update File: src/lib/apiClient.ts",
            "*** Add File: src/lib/newClient.ts",
            "*** Add File: src/lib/otherClient.ts",
            "*** End Patch",
        ])
        with pytest.raises(SystemExit) as error:
            _run_main(monkeypatch, {
                "tool_name": "apply_patch", "tool_input": {"command": patch},
                "cwd": str(repo_root / "frontend"),
            })
        assert error.value.code == 2
        warning = capsys.readouterr().err
        assert "newClient.ts" in warning
        assert "otherClient.ts" in warning
        assert "apiClient.ts" not in warning

    def test_move_checks_destination_and_ignores_delete(self, tmp_path, monkeypatch, capsys):
        repo_root = _make_repo(tmp_path, [])
        _write_target_file(repo_root, "frontend/src/lib/newClient.ts")
        patch = "\n".join([
            "*** Begin Patch",
            "*** Delete File: frontend/src/lib/deleted.ts",
            "*** Update File: frontend/src/lib/oldClient.ts",
            "*** Move to: frontend/src/lib/newClient.ts",
            "*** End Patch",
        ])
        with pytest.raises(SystemExit):
            _run_main(monkeypatch, {
                "tool_input": {"command": patch}, "cwd": str(repo_root),
            })
        warning = capsys.readouterr().err
        assert "newClient.ts" in warning
        assert "oldClient.ts" not in warning
        assert "deleted.ts" not in warning

    @pytest.mark.parametrize("tool_input", [None, [], "invalid", {"command": []}])
    def test_invalid_tool_input_is_ignored(self, tmp_path, monkeypatch, capsys, tool_input):
        _run_main(monkeypatch, {"tool_input": tool_input, "cwd": str(tmp_path)})
        assert capsys.readouterr().err == ""
