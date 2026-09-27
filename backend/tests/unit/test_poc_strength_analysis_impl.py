"""ルールベース解析エンジン(services/poc_strength/analysis.py)の実装テスト。

閾値の境界・根拠抽出・評価保留の判定を、台本に依存しない最小の入力で検証する。
"""

import pytest

from caliboo_api.services.poc_strength import analysis
from caliboo_api.services.poc_strength.fan_in import merge_reviews
from caliboo_api.services.poc_strength.skill_catalog import find_skill

_EMPTY = "特筆すべき出来事はなかった。"


def _iteration(number: int, worker_output: str, trainer_feedback: str = _EMPTY) -> dict:
    return {
        "iteration": number,
        "task": {
            "taskId": f"t_{number}",
            "title": "作業",
            "description": "説明",
            "skillHint": None,
        },
        "workerOutput": worker_output,
        "trainerFeedback": trainer_feedback,
    }


def _diary(keep: str = _EMPTY) -> dict:
    return {
        "date": "2026-09-24",
        "tasks": [
            {"time": "09:00-10:00", "what": "作業", "progressDesc": _EMPTY, "progressRate": 100}
        ],
        "feelings": {"emotion": "たのしい", "trigger": _EMPTY, "nextAction": _EMPTY},
        "kpt": {"keep": keep, "problem": _EMPTY, "try": _EMPTY},
        "mentorComment": _EMPTY,
    }


def _review_comment(agent_key: str, role: str, tone: str, comment: str, flags: list[str]) -> dict:
    return {
        "agentKey": agent_key,
        "reviewerRole": role,
        "magiTone": tone,
        "comment": comment,
        "flags": flags,
    }


def _review(comment: str = _EMPTY) -> list[dict]:
    return [_review_comment("alpha", "管理職", "MELCHIOR", comment, [])]


def _analyze(trajectory: list[dict], diary: dict, reviews: list[dict]) -> dict:
    return analysis.analyze(
        subject_id="emp_x",
        run_id="run_0001",
        trajectory=trajectory,
        diary=diary,
        reviews=reviews,
        generated_at="2026-09-24T00:00:00+00:00",
        provider_name="rule_based_v1",
    )


def _codes(result: dict) -> list[str]:
    return [item["layerTask"]["skillCode"] for item in result["strengths"]]


def test_no_keyword_anywhere_produces_no_strength():
    result = _analyze([_iteration(1, _EMPTY)], _diary(), _review())

    assert result["strengths"] == []
    assert result["overallStatus"] == "insufficient"


@pytest.mark.parametrize(
    ("worker", "keep", "comment", "expected_status", "expected_confidence"),
    [
        ("SQLを書いた。", _EMPTY, _EMPTY, "insufficient_evidence", 0.35),
        ("SQLを書いた。", "SQLの検証を続ける。", _EMPTY, "tentative", 0.6),
        ("SQLを書いた。", "SQLの検証を続ける。", "SQLの設計が良い。", "confirmed", 0.85),
    ],
)
def test_support_kind_count_decides_status(
    worker, keep, comment, expected_status, expected_confidence
):
    """裏付けの「種類数」(軌跡/日報/レビュー)だけで確信度が決まる。"""
    result = _analyze([_iteration(1, worker)], _diary(keep), _review(comment))

    strength = result["strengths"][0]
    assert strength["layerTask"]["skillCode"] == "DBAD"
    assert strength["status"] == expected_status
    assert strength["confidence"] == expected_confidence


def test_confidence_does_not_grow_with_repetition_within_one_kind():
    """同じ種類の中で何度言及されても確信度は上がらない(記述量に引きずられない)。"""
    once = _analyze([_iteration(1, "SQLを書いた。")], _diary(), _review())
    many = _analyze(
        [
            _iteration(1, "SQLを書いた。クエリを直した。テーブルを整えた。"),
            _iteration(2, "集計した。インデックスを張った。結合した。"),
        ],
        _diary(),
        _review(),
    )

    assert once["strengths"][0]["confidence"] == many["strengths"][0]["confidence"] == 0.35


def test_level_is_two_only_when_fully_supported():
    supported = _analyze([_iteration(1, "SQLを書いた。")], _diary("SQLを検証する。"), _review("SQLが良い。"))
    partial = _analyze([_iteration(1, "SQLを書いた。")], _diary("SQLを検証する。"), _review())

    assert supported["strengths"][0]["layerTask"]["level"] == 2
    assert partial["strengths"][0]["layerTask"]["level"] == 1


def test_held_back_strength_has_no_quadrant_but_keeps_evidence():
    result = _analyze([_iteration(1, "SQLを書いた。")], _diary(), _review())

    strength = result["strengths"][0]
    assert strength["status"] == "insufficient_evidence"
    assert strength["layerWillSkill"] is None
    assert len(strength["evidence"]) == 1


def test_evidence_is_extracted_as_the_matching_sentence_with_source():
    result = _analyze(
        [_iteration(1, "前置きの文。クエリを組み立てた。後置きの文。")],
        _diary(),
        _review(),
    )

    evidence = result["strengths"][0]["evidence"][0]
    assert evidence["quote"] == "クエリを組み立てた。"
    assert evidence["source"] == {"kind": "trajectory", "iteration": 1, "field": "workerOutput"}


def test_evidence_is_limited_to_one_quote_per_kind():
    result = _analyze(
        [_iteration(1, "SQLを書いた。"), _iteration(2, "クエリを直した。")],
        _diary("テーブルを整えた。"),
        _review("結合が正しい。"),
    )

    evidence = result["strengths"][0]["evidence"]
    assert len(evidence) == 3
    assert [item["source"]["kind"] for item in evidence] == ["trajectory", "diary", "review"]


def test_task_definition_is_used_only_when_nothing_better_matches():
    trajectory = [_iteration(1, _EMPTY)]
    trajectory[0]["task"]["title"] = "クエリを作る"

    result = _analyze(trajectory, _diary(), _review())

    evidence = result["strengths"][0]["evidence"][0]
    assert evidence["source"]["field"] == "task.title"


def test_learning_agility_reports_growth_between_active_iterations():
    trajectory = [
        _iteration(1, "SQLを書いた。"),
        _iteration(2, "SQLとクエリとテーブルを見直した。"),
        _iteration(3, _EMPTY),
    ]

    result = _analyze(trajectory, _diary(), _review())

    agility = result["strengths"][0]["learningAgility"]
    assert agility["delta"] == "+"
    assert agility["note"] == "1周目から2周目にかけて、言及が増えた"


def test_learning_agility_ignores_iterations_where_the_skill_is_absent():
    """後半でタスクの対象が変わっただけの周回を「衰退」と誤判定しない。"""
    trajectory = [
        _iteration(1, "SQLとクエリを書いた。"),
        _iteration(2, "SQLとクエリを直した。"),
        _iteration(3, "今日は文章をまとめた。"),
    ]

    result = _analyze(trajectory, _diary(), _review())

    database_skill = next(
        item for item in result["strengths"] if item["layerTask"]["skillCode"] == "DBAD"
    )
    assert database_skill["learningAgility"]["delta"] == "0"
    assert database_skill["learningAgility"]["note"] == "1周目から2周目にかけて、安定して現れている"


def test_learning_agility_reports_decline():
    trajectory = [
        _iteration(1, "SQLとクエリとテーブルを扱った。"),
        _iteration(2, _EMPTY),
        _iteration(3, "SQLだけ触った。"),
    ]

    result = _analyze(trajectory, _diary(), _review())

    agility = result["strengths"][0]["learningAgility"]
    assert agility["delta"] == "-"
    assert agility["note"] == "1周目から3周目にかけて、言及が減った"


def test_learning_agility_is_not_evaluated_with_a_single_observation():
    result = _analyze([_iteration(1, "SQLを書いた。"), _iteration(2, _EMPTY)], _diary(), _review())

    agility = result["strengths"][0]["learningAgility"]
    assert agility["delta"] == "0"
    assert agility["note"] == "継続して観測できる周回が不足しているため成長は評価できない"


@pytest.mark.parametrize(
    ("first", "second", "comment", "expected_quadrant"),
    [
        ("SQLを書いた。", "SQLとクエリを直した。", "SQLが良い。", "High Will / High Skill"),
        ("SQLとクエリを書いた。", "SQLだけ直した。", "SQLが良い。", "Low Will / High Skill"),
        ("SQLを書いた。", "SQLとクエリを直した。", _EMPTY, "High Will / Low Skill"),
        ("SQLとクエリを書いた。", "SQLだけ直した。", _EMPTY, "Low Will / Low Skill"),
    ],
)
def test_quadrant_uses_learning_agility_for_the_will_axis(
    first, second, comment, expected_quadrant
):
    """Will軸には確信度ではなく、周回間の伸びと継続性を使う。

    レビューでの裏付けの有無(comment)が裏付けの種類数を変え、Skill軸(SFIAレベル)を動かす。
    """
    trajectory = [_iteration(1, first), _iteration(2, second), _iteration(3, _EMPTY)]

    result = _analyze(trajectory, _diary("SQLを検証する。"), _review(comment))

    assert result["strengths"][0]["layerWillSkill"]["quadrant"] == expected_quadrant


def test_growth_action_for_high_will_low_skill_matches_the_spec_example():
    """仕様書§7の例: High Will / Low Skill → 基礎課題の反復で底上げする。"""
    trajectory = [_iteration(1, "SQLを書いた。"), _iteration(2, "SQLとクエリを直した。")]

    result = _analyze(trajectory, _diary("SQLを検証する。"), _review())

    will_skill = result["strengths"][0]["layerWillSkill"]
    assert will_skill["quadrant"] == "High Will / Low Skill"
    assert "基礎課題の反復" in will_skill["policy"]


def test_growth_content_is_attached_by_skill_code():
    trajectory = [_iteration(1, "SQLを書いた。"), _iteration(2, "SQLを直した。")]

    result = _analyze(trajectory, _diary("SQLを検証する。"), _review("SQLが良い。"))

    assert result["strengths"][0]["growthContent"]["contentTag"] == "sql-drill"


def test_strength_without_sustained_observation_gets_no_quadrant_or_growth_action():
    """Will軸を評価できない強みは、象限も育成アクションも出さない。

    確信度は足りていても(3種類の裏付けで確定)、周回をまたいだ観測が無ければ
    「意欲が低い」とは言えないため、断定せずに空欄にする。
    """
    result = _analyze(
        [_iteration(1, "SQLを書いた。"), _iteration(2, _EMPTY)],
        _diary("SQLを検証する。"),
        _review("SQLが良い。"),
    )

    strength = result["strengths"][0]
    assert strength["status"] == "confirmed"
    assert strength["learningAgility"]["note"] == "継続して観測できる周回が不足しているため成長は評価できない"
    assert strength["layerWillSkill"] is None
    assert strength["growthContent"] is None


@pytest.mark.parametrize(
    ("keep", "comment", "expected_overall"),
    [
        (_EMPTY, _EMPTY, "insufficient"),
        ("SQLを検証する。", _EMPTY, "partial"),
        ("SQLを検証する。", "SQLが良い。", "complete"),
    ],
)
def test_overall_status_is_derived_from_each_status(keep, comment, expected_overall):
    result = _analyze([_iteration(1, "SQLを書いた。")], _diary(keep), _review(comment))

    assert result["overallStatus"] == expected_overall


def test_notes_are_derived_from_the_overall_status():
    """補足文を全体判定から一意に引く(判定と食い違う文が出ないようにする)。"""
    held = _analyze([_iteration(1, "SQLを書いた。")], _diary(), _review())
    partial = _analyze([_iteration(1, "SQLを書いた。")], _diary("SQLを検証する。"), _review())
    settled = _analyze(
        [_iteration(1, "SQLを書いた。")], _diary("SQLを検証する。"), _review("SQLが良い。")
    )

    assert held["overallStatus"] == "insufficient"
    assert held["notes"] == "根拠が不足するため、断定できる強みは無いと判断した"
    assert partial["overallStatus"] == "partial"
    assert partial["notes"] == "根拠が揃わない領域は暫定・評価保留とした"
    assert settled["overallStatus"] == "complete"
    assert settled["notes"] == "全ての強みについて十分な根拠が確認できた"


def test_output_carries_identity_and_provider():
    result = _analyze([_iteration(1, "SQLを書いた。")], _diary(), _review())

    assert result["subjectId"] == "emp_x"
    assert result["runId"] == "run_0001"
    assert result["generatedAt"] == "2026-09-24T00:00:00+00:00"
    assert result["provider"] == "rule_based_v1"


def test_strengths_follow_the_catalog_order():
    result = _analyze(
        [_iteration(1, "クエリとダッシュボードを作り、ヒアリングもした。")],
        _diary(),
        _review(),
    )

    assert _codes(result) == ["DBAD", "DTAN", "RLMT"]


def test_themes_come_from_the_skill_catalog():
    result = _analyze([_iteration(1, "SQLを書いた。")], _diary(), _review())

    strength = result["strengths"][0]
    assert strength["layerBehavior"]["themes"] == list(find_skill("DBAD").themes)
    assert strength["layerBehavior"]["framework"] == "CliftonStrengths"


def test_fan_in_merges_comments_and_deduplicates_flags():
    reviews = [
        _review_comment("alpha", "管理職", "MELCHIOR", "所見A", ["X"]),
        _review_comment("beta", "講師", "BALTHASAR", "所見B", ["X", "Y"]),
        _review_comment("gamma", "シニアエンジニア", "CASPER", "所見C", []),
    ]

    merged = merge_reviews(reviews)

    assert merged["fanInFlags"] == ["X", "Y"]
    assert "[管理職(MELCHIOR)] 所見A" in merged["fanInComment"]
    assert "[講師(BALTHASAR)] 所見B" in merged["fanInComment"]
    assert "[シニアエンジニア(CASPER)] 所見C" in merged["fanInComment"]


def test_fan_in_falls_back_to_reviewer_role_for_unknown_agent_key():
    merged = merge_reviews([_review_comment("delta", "人事", "-", "所見D", [])])

    assert merged["fanInComment"] == "[人事] 所見D"


def test_find_skill_returns_none_for_unknown_code():
    assert find_skill("NOPE") is None
