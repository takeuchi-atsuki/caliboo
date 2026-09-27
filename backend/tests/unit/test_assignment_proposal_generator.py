"""ルールベース課題案生成器(services/assignment_proposal/providers.py)の仕様テスト。

テーマ選択の重み・同点・除外・フォールバック・気分/進捗材料・材料の並び・決定論性を、
`docs/test-perspectives.md`の「AIの課題案」節に対応する最小の入力で検証する。
"""

from caliboo_api.services.assignment_proposal.providers import RuleBasedProposalGenerator
from caliboo_api.services.assignment_proposal.theme_catalog import FALLBACK_THEME_KEY

_NEUTRAL = "特筆すべき出来事は無かった。"


def _report(date, problem=_NEUTRAL, try_=_NEUTRAL, keep=_NEUTRAL, mood=None, mood_comment=_NEUTRAL):
    return {
        "date": date,
        "problem": problem,
        "try": try_,
        "keep": keep,
        "mood": mood or [],
        "moodComment": mood_comment,
    }


def _generate(reports=None, submission_statuses=None, feedbacks=None, excluded_themes=None):
    generator = RuleBasedProposalGenerator()
    return generator.generate(
        member_name="ハルカ",
        reports=reports or [],
        submission_statuses=submission_statuses or [],
        feedbacks=feedbacks or [],
        excluded_themes=excluded_themes or set(),
    )


# --- テーマ選択・重み ---


def test_problem_field_weighs_more_than_keep_field():
    """観点: Problem・Try・講師FBの記述がKeep・きもちより強く効く(Problem側)。

    Gitキーワードは弱い欄(Keep)に3回、SQLキーワードは強い欄(Problem)に2回だけ
    出現させ、出現回数で劣るSQL側(4点)がGit側(3点)より勝つことを確認する。
    """
    reports = [
        _report("2026-09-01", keep="Gitのブランチ運用で戸惑った。"),
        _report("2026-09-02", keep="ブランチの切り方がまだ分からない。"),
        _report("2026-09-03", keep="コミットの粒度に迷った。"),
        _report("2026-09-04", problem="テーブルのJOINで結果がずれた。"),
        _report("2026-09-05", problem="SQLのJOINをまた間違えた。"),
    ]

    result = _generate(reports=reports)

    assert result["themeKey"] == "sql_join"


def test_try_field_weighs_more_than_mood_comment_field():
    """観点: Try欄(重み2)の一致が、きもちコメント欄(重み1)の一致より強く効く。

    Gitキーワードはきもちコメントに3回、SQLキーワードはTryに2回だけ出現させ、
    出現回数で劣るSQL側(4点)がGit側(3点)より勝つことを確認する。
    """
    reports = [
        _report("2026-09-01", mood_comment="Gitのブランチ運用で戸惑った。"),
        _report("2026-09-02", mood_comment="ブランチの切り方がまだ分からない。"),
        _report("2026-09-03", mood_comment="コミットの粒度に迷った。"),
        _report("2026-09-04", try_="テーブルのJOINを復習する。"),
        _report("2026-09-05", try_="SQLのJOINを復習する。"),
    ]

    result = _generate(reports=reports)

    assert result["themeKey"] == "sql_join"


def test_matching_sentence_becomes_quoted_material():
    reports = [_report("2026-09-10", problem="SQLのJOINで結果がずれてしまった。")]

    result = _generate(reports=reports)

    quotes = [m for m in result["materials"] if m["kind"] == "report"]
    assert quotes == [
        {
            "kind": "report",
            "date": "2026-09-10",
            "quote": "SQLのJOINで結果がずれてしまった。",
            "sourceLabel": "日報 Problem",
        }
    ]


# --- 同点・除外・フォールバック ---


def test_tie_is_broken_by_catalog_order():
    """観点: 同じ入力なら同じテーマが選ばれ、同点はカタログ順(Git運用が会議・用語より先)。"""
    reports = [
        _report("2026-09-01", problem="Gitのブランチ運用で困った。"),
        _report("2026-09-02", problem="会議で専門用語が分からなかった。"),
    ]

    result = _generate(reports=reports)

    assert result["themeKey"] == "git_workflow"


def test_excluded_theme_is_skipped_in_favor_of_next_candidate():
    """観点: 配信済み・見送り済みのテーマは次の課題案で選ばれない。"""
    reports = [
        _report("2026-09-01", problem="Gitのブランチ運用で困った。"),
        _report("2026-09-02", problem="会議で専門用語が分からなかった。"),
    ]

    result = _generate(reports=reports, excluded_themes={"git_workflow"})

    assert result["themeKey"] == "meeting_terms"


def test_fallback_theme_is_used_when_all_matching_themes_are_excluded():
    """観点: 一致するテーマが1つしかなく、それが除外済みならふりかえりになる
    (「一致テーマ全除外→ふりかえり」)。"""
    reports = [_report("2026-09-01", problem="Gitのブランチ運用で困った。")]

    result = _generate(reports=reports, excluded_themes={"git_workflow"})

    assert result["themeKey"] == FALLBACK_THEME_KEY


def test_fallback_theme_is_used_when_nothing_matches():
    """観点: どのテーマにも当てはまらなければふりかえりの汎用課題になる。"""
    reports = [_report("2026-09-01"), _report("2026-09-02")]

    result = _generate(reports=reports)

    assert result["themeKey"] == FALLBACK_THEME_KEY
    assert not [m for m in result["materials"] if m["kind"] in ("report", "feedback")]


def test_fallback_theme_is_not_excluded_even_if_previously_used():
    """観点: フォールバックは除外テーマの対象にならない(常に選び直せる)。"""
    reports = [_report("2026-09-01"), _report("2026-09-02")]

    result = _generate(reports=reports, excluded_themes={FALLBACK_THEME_KEY})

    assert result["themeKey"] == FALLBACK_THEME_KEY


def test_feedback_matches_are_scored_and_quoted():
    feedbacks = [{"date": "2026-09-11", "comment": "テーブルのJOINの使い方を復習しましょう。"}]

    result = _generate(feedbacks=feedbacks)

    assert result["themeKey"] == "sql_join"
    quotes = [m for m in result["materials"] if m["kind"] == "feedback"]
    assert quotes == [
        {
            "kind": "feedback",
            "date": "2026-09-11",
            "quote": "テーブルのJOINの使い方を復習しましょう。",
            "sourceLabel": "講師フィードバック",
        }
    ]


# --- 気分・進捗材料 ---


def test_mood_material_appears_when_three_of_five_recent_reports_are_foggy_or_tired():
    reports = [
        _report("2026-09-05", mood=["tired"]),
        _report("2026-09-04", mood=["foggy"]),
        _report("2026-09-03", mood=["happy"]),
        _report("2026-09-02", mood=["tired"]),
        _report("2026-09-01", mood=["fun"]),
    ]

    result = _generate(reports=reports)

    mood_materials = [m for m in result["materials"] if m["kind"] == "mood"]
    assert len(mood_materials) == 1
    assert mood_materials[0]["sourceLabel"] == "直近のきもち"
    assert mood_materials[0]["date"] is None


def test_mood_material_is_absent_when_fewer_than_three_are_foggy_or_tired():
    reports = [
        _report("2026-09-05", mood=["tired"]),
        _report("2026-09-04", mood=["foggy"]),
        _report("2026-09-03", mood=["happy"]),
        _report("2026-09-02", mood=["fun"]),
        _report("2026-09-01", mood=["fun"]),
    ]

    result = _generate(reports=reports)

    assert not [m for m in result["materials"] if m["kind"] == "mood"]


def test_progress_material_appears_when_there_is_a_not_submitted_assignment():
    result = _generate(submission_statuses=["not_submitted", "submitted", "reviewed"])

    progress_materials = [m for m in result["materials"] if m["kind"] == "progress"]
    assert len(progress_materials) == 1
    assert progress_materials[0]["sourceLabel"] == "課題の進捗"
    assert result["progress"] == {
        "submittedCount": 2,
        "reviewedCount": 1,
        "notSubmittedCount": 1,
        "recentMoods": [],
    }


def test_progress_material_is_absent_when_everything_is_submitted():
    result = _generate(submission_statuses=["submitted", "reviewed"])

    assert not [m for m in result["materials"] if m["kind"] == "progress"]
    assert result["progress"]["notSubmittedCount"] == 0


def test_progress_recent_moods_reflects_first_mood_of_each_recent_report_newest_first():
    reports = [
        _report("2026-09-05", mood=["tired", "foggy"]),
        _report("2026-09-04", mood=["happy"]),
        _report("2026-09-03", mood=[]),
    ]

    result = _generate(reports=reports)

    assert result["progress"]["recentMoods"] == ["tired", "happy"]


# --- 材料の並び ---


def test_materials_are_ordered_by_date_desc_then_field_order():
    reports = [
        _report("2026-09-01", problem="報告の結論が伝わらず困った。", try_="次は結論から話す。"),
        _report("2026-09-03", problem="報告で結論が伝わらなかった。"),
    ]

    result = _generate(reports=reports)

    quotes = [m for m in result["materials"] if m["kind"] == "report"]
    assert [(m["date"], m["sourceLabel"]) for m in quotes] == [
        ("2026-09-03", "日報 Problem"),
        ("2026-09-01", "日報 Problem"),
        ("2026-09-01", "日報 Try"),
    ]


def test_keep_and_mood_comment_are_ordered_after_problem_and_try_on_the_same_date():
    """観点: Keep・きもちコメントの並び順(同日ならProblem→Try→Keep→きもちの欄順)。"""
    reports = [
        _report(
            "2026-09-01",
            problem="報告の結論が伝わらず困った。",
            try_="次は結論から話す。",
            keep="報告の要点を先にメモできた。",
            mood_comment="報告がうまく伝わらずもやもやした。",
        ),
    ]

    result = _generate(reports=reports)

    quotes = [m for m in result["materials"] if m["kind"] == "report"]
    assert [m["sourceLabel"] for m in quotes] == [
        "日報 Problem",
        "日報 Try",
        "日報 Keep",
        "日報 きもち",
    ]


# --- 決定論性 ---


def test_generation_is_deterministic_for_the_same_input():
    reports = [
        _report("2026-09-05", problem="報告の結論が伝わりにくかった。", mood=["tired"]),
        _report("2026-09-04", mood=["foggy"]),
        _report("2026-09-03", mood=["tired"]),
    ]
    submission_statuses = ["not_submitted", "submitted"]
    feedbacks = [{"date": "2026-09-02", "comment": "結論から話す練習をしましょう。"}]

    first = _generate(
        reports=reports, submission_statuses=submission_statuses, feedbacks=feedbacks
    )
    second = _generate(
        reports=reports, submission_statuses=submission_statuses, feedbacks=feedbacks
    )

    assert first == second
