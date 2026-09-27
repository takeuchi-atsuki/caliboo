#!/usr/bin/env python3
"""
PostToolUse フック(matcher: Write|Edit): frontendでロジックを持つファイル
(`frontend/src/lib/*.ts`・`frontend/src/features/*/use*.ts`)を編集した際、
`frontend/vite.config.ts`の`test.coverage.include`にそのパスが列挙されているかを
検査し、未列挙であれば警告する。

処理はブロックしない。既にツール呼び出しは完了しているためPostToolUseでの
「ブロック」は編集の取り消しを意味せず、exit code 2 で stderr を Claude へ
フィードバックするだけである。dev-flowプラグインの`docs/hooks.md`が記す通り、
PreToolUse/PostToolUse/Stop の stdout はtranscriptモード(Ctrl+O)を開かない限り
ユーザーに見えないため、Claudeへ確実に伝える経路として exit code 2 を使う
(`.claude/CLAUDE.md`のCaliboo版チェックリストからCLAUDEが辿って対応する想定)。

NOTE: 入力不正時・判定不能時はfail-open(何も出力せず正常終了)。

テストは.claude/hooks/test_coverage_include_warning.py。
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


def main() -> None:
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path")
        cwd = data.get("cwd")
    except Exception:
        return

    if not file_path or not isinstance(file_path, str):
        return
    if not cwd or not isinstance(cwd, str):
        return

    relative_path = _relative_path(file_path, cwd)
    if relative_path is None or not _matches_target(relative_path):
        return

    listed = _is_listed_in_coverage_include(Path(cwd), relative_path)
    if listed is not False:
        # True(列挙済み)・None(vite.config.tsが読めず判定不能)はどちらも警告しない。
        return

    print(
        f"⚠️ {relative_path} は frontend/vite.config.ts の test.coverage.include に"
        "含まれていません。ロジックを持つファイルであれば、単体テスト追加とあわせて"
        "coverage.include への追記を検討してください"
        "(caliboo-test-check skill・.claude/rules/typescript.md参照)。",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
