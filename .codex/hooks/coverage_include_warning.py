#!/usr/bin/env python3
"""Codex PostToolUse: apply_patchで編集したロジックファイルのcoverage.includeを確認する。

tool_input.commandのパッチから追加・更新・移動先を取り出す。
未列挙ならexit 2とstderrでCodexへフィードバックする(編集は取り消さない)。
file_path形式も受け付ける。入力不正・判定不能時はfail-open。
テスト: python3 -m pytest .codex/hooks/
"""

import json
import re
import sys
from pathlib import Path

_TARGET_PATTERNS = (
    re.compile(r"^frontend/src/lib/[^/]+\.ts$"),
    re.compile(r"^frontend/src/features/[^/]+/use[^/]+\.ts$"),
)


def _matches_target(relative_path: str) -> bool:
    return any(pattern.match(relative_path) for pattern in _TARGET_PATTERNS)


def _relative_path(file_path: str, cwd: str) -> str | None:
    """`file_path`を`cwd`(リポジトリルート想定)からの相対パスへ変換する。
    `cwd`配下でない、またはパス解決に失敗した場合はNoneを返す。"""
    try:
        return str(Path(file_path).resolve().relative_to(Path(cwd).resolve()))
    except (OSError, ValueError):
        return None


def _is_listed_in_coverage_include(repo_root: Path, relative_path: str) -> bool | None:
    """`frontend/vite.config.ts`のcoverage.includeに、`frontend/`を除いた
    `src/...`形式の`relative_path`が含まれるかを判定する。
    `vite.config.ts`が読めない場合はNoneを返す(判定不能)。

    !NOTE: TypeScriptをパースせず文字列検索で判定する。coverage.includeの各要素は
           `"src/..."`形式の文字列リテラルであり、フォーマットが崩れない限り
           文字列検索で十分。厳密なAST解析はこの用途には過剰。
    """
    config_path = repo_root / "frontend" / "vite.config.ts"
    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError:
        return None

    src_relative = relative_path[len("frontend/"):]
    return f'"{src_relative}"' in content


def _edited_paths(tool_input: dict) -> list[str]:
    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path:
        return [file_path]
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.startswith("*** Begin Patch\n"):
        return []
    paths = []
    for line in command.splitlines():
        for prefix in ("*** Add File: ", "*** Update File: ", "*** Move to: "):
            if line.startswith(prefix):
                paths.append(line[len(prefix):])
    return list(dict.fromkeys(paths))


def _repo_root(cwd: Path) -> Path:
    for parent in (cwd, *cwd.parents):
        if (parent / ".git").exists() or (parent / "frontend/vite.config.ts").is_file():
            return parent
    return cwd


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        return
    if not isinstance(data, dict):
        return
    tool_input = data.get("tool_input", {})
    cwd = data.get("cwd")
    if not isinstance(tool_input, dict) or not isinstance(cwd, str) or not cwd:
        return
    cwd_path = Path(cwd).resolve()
    repo_root = _repo_root(cwd_path)
    warned = False
    for file_path in _edited_paths(tool_input):
        path = Path(file_path)
        if not path.is_absolute():
            path = cwd_path / path
        relative_path = _relative_path(str(path), str(repo_root))
        if relative_path is None or not _matches_target(relative_path):
            continue
        if not path.is_file():
            continue  # 削除・移動元は対象外。
        if _is_listed_in_coverage_include(repo_root, relative_path) is not False:
            continue
        print(
            f"⚠️ {relative_path} は frontend/vite.config.ts の test.coverage.include に"
            "含まれていません。ロジックを持つファイルであれば、単体テスト追加とあわせて"
            "coverage.include への追記を検討してください"
            "(caliboo-test-check skill・.codex/rules/typescript.md参照)。",
            file=sys.stderr,
        )
        warned = True
    if warned:
        sys.exit(2)


if __name__ == "__main__":
    main()
