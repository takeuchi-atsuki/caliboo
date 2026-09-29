"""標準ライブラリだけで独立した期待値とSQLite実測を照合する。"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent

# SQLの実行結果から計算しない期待値。意図した教材データを先に固定する。
EXPECTED = {
    "inner_join": [[10, 1, 201], [10, 2, 202], [11, 1, 203], [11, 3, 204]],
    "left_join": [
        [10, 1, 201], [10, 2, 202], [10, 3, None], [10, 4, None],
        [11, 1, 203], [11, 2, None], [11, 3, 204], [11, 4, None],
    ],
    "group_by": [[10, 2, 1, 90.0], [11, 2, 2, 75.0]],
    "missing_submissions": [[10, 3], [10, 4], [11, 2], [11, 4]],
    "null_and_count": [[1, 2, 2, 2, 2], [2, 1, 1, 1, 0],
                       [3, 1, 0, 0, 0], [4, 1, 0, 0, 0]],
    "null_state": [[1, "採点済み"], [2, "提出済み・未採点"],
                   [3, "未提出"], [4, "未提出"]],
}

EXPLANATIONS = {
    "inner_join": "INNER JOINは提出済み4組だけを返し、未提出4組を落とす。",
    "left_join": "LEFT JOINは全8組を保ち、未提出のsubmission_idをNULLにする。",
    "group_by": "SQL課題は提出2件、採点済み1件で平均90点。3D課題は2件とも採点済みで平均75点。",
    "missing_submissions": "提出行のIDがNULLの4組だけが未提出。点数NULLの井上は含まれない。",
    "null_and_count": "COUNT(*)は結合後の行を数える。COUNT(r.id)は日報なしを0、COUNT(s.score)は未採点を0とする。",
    "null_state": "点数NULLだけでは未提出と未採点を区別できず、提出行IDで分岐する。",
}


def read_queries() -> dict[str, str]:
    source = (ROOT / "exercises.sql").read_text(encoding="utf-8")
    parts = re.split(r"(?m)^-- name: ([a-z_]+)\s*$", source)
    if parts[0].strip() or len(parts) != 1 + 2 * len(EXPECTED):
        raise ValueError("exercises.sqlの設問数が期待値と一致しません")
    queries = dict(zip(parts[1::2], parts[2::2], strict=True))
    if queries.keys() != EXPECTED.keys():
        raise ValueError("設問名または順番が期待値と一致しません")
    return queries


def main() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise AssertionError("外部キー制約が有効ではありません")

    results = []
    for name, query in read_queries().items():
        actual = [list(row) for row in connection.execute(query).fetchall()]
        expected = EXPECTED[name]
        results.append({"question": name, "expected": expected,
                        "actual": actual, "passed": actual == expected,
                        "explanation": EXPLANATIONS[name]})

    before = connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    constraint_error = None
    try:
        connection.execute(
            "INSERT INTO submissions VALUES (205, 10, 999, 50)"
        )
    except sqlite3.IntegrityError as error:
        constraint_error = str(error)
    after_constraint = connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    constraint_passed = (
        constraint_error == "FOREIGN KEY constraint failed"
        and before == after_constraint == 4
    )
    results.append({"question": "foreign_key", "expected":
                    {"error": "FOREIGN KEY constraint failed", "count": 4},
                    "actual": {"error": constraint_error, "count": after_constraint},
                    "passed": constraint_passed,
                    "explanation": "存在しない利用者への提出は外部キー制約で拒否され、件数は変わらない。"})

    connection.commit()
    connection.execute("BEGIN")
    connection.execute("INSERT INTO submissions VALUES (205, 10, 3, 60)")
    during = connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    connection.rollback()
    after_rollback = connection.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    restored = connection.execute(
        "SELECT COUNT(*) FROM submissions WHERE id = 205"
    ).fetchone()[0]
    results.append({"question": "rollback", "expected":
                    {"before": 4, "during": 5, "after": 4, "new_row": 0},
                    "actual": {"before": before, "during": during,
                               "after": after_rollback, "new_row": restored},
                    "passed": (before, during, after_rollback, restored) == (4, 5, 4, 0),
                    "explanation": "有効な追加をBEGIN内で実施後、ROLLBACKで件数と行を元に戻す。"})
    connection.close()

    report = {"database": ":memory:", "sqlite_version": sqlite3.sqlite_version,
              "all_passed": all(item["passed"] for item in results),
              "results": results}
    (ROOT / "exercise-results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = ["# SQLite 演習結果", "", f"SQLite {sqlite3.sqlite_version} / メモリDB", ""]
    for item in results:
        lines.extend([f"## {item['question']}", "", item["explanation"], "",
                      "期待値:", "", "```json",
                      json.dumps(item["expected"], ensure_ascii=False, indent=2),
                      "```", "", "実測値:", "", "```json",
                      json.dumps(item["actual"], ensure_ascii=False, indent=2),
                      "```", "", f"照合: {'成功' if item['passed'] else '失敗'}", ""])
    (ROOT / "exercise-results.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{sum(item['passed'] for item in results)}/{len(results)} 問一致")
    if not report["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
