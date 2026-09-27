"""強み解析PoCのDB層・オーケストレーション層(data/poc_strength_data.py、
services/poc_strength/pipeline.py・providers.py)の実装テスト。"""

import pytest

from caliboo_api.data import poc_strength_data
from caliboo_api.data.poc_persona_scripts import PERSONA_SCRIPTS, find_script
from caliboo_api.services.poc_strength.pipeline import (
    UnknownPersonaError,
    import_run,
    run_pipeline,
)
from caliboo_api.services.poc_strength.providers import AuthoredMockProvider


def _minimal_import_payload(**overrides):
    """`pipeline.import_run()`用の最小ペイロード(dictそのまま。Pydanticの検証は通さない)。

    軌跡(iteration1)・日報・レビュー(alpha)それぞれにDBADのキーワード(「SQL」「クエリ」
    「集計」)を1件含め、`test_import_run_does_not_pass_*`系が「意味のある検出結果が
    経路によって変わらない」ことを確かめられるようにしている。
    """
    payload = {
        "personaKey": "external_claude",
        "subjectId": "emp_101",
        "label": "test run",
        "injectedPersona": None,
        "trajectory": [
            {
                "iteration": 1,
                "task": {
                    "taskId": "t1",
                    "title": "task1",
                    "description": "desc",
                    "skillHint": None,
                },
                "workerOutput": "SQLクエリで集計しました。",
                "trainerFeedback": "feedback1",
                "humanOverride": None,
            },
            {
                "iteration": 2,
                "task": {
                    "taskId": "t2",
                    "title": "task2",
                    "description": "desc",
                    "skillHint": None,
                },
                "workerOutput": "output2",
                "trainerFeedback": "feedback2",
                "humanOverride": None,
            },
            {
                "iteration": 3,
                "task": {
                    "taskId": "t3",
                    "title": "task3",
                    "description": "desc",
                    "skillHint": None,
                },
                "workerOutput": "output3",
                "trainerFeedback": "feedback3",
                "humanOverride": None,
            },
        ],
        "diary": {
            "date": "2026-09-24",
            "tasks": [
                {
                    "time": "09:00",
                    "what": "集計クエリ作成",
                    "progressDesc": "done",
                    "progressRate": 100,
                }
            ],
            "feelings": {"emotion": "e", "trigger": "t", "nextAction": "n"},
            "kpt": {"keep": "k", "problem": "p", "try": "t"},
        },
        "reviews": [
            {
                "agentKey": "alpha",
                "reviewerRole": "管理職",
                "magiTone": "MELCHIOR",
                "comment": "クエリの構成が良い。",
                "flags": [],
            },
            {
                "agentKey": "beta",
                "reviewerRole": "講師",
                "magiTone": "BALTHASAR",
                "comment": "c2",
                "flags": [],
            },
            {
                "agentKey": "gamma",
                "reviewerRole": "シニアエンジニア",
                "magiTone": "CASPER",
                "comment": "c3",
                "flags": [],
            },
        ],
        "trace": {"generationProvider": "claude_session", "agents": []},
        "externalStrengths": None,
    }
    payload.update(overrides)
    return payload


def test_create_run_formats_run_id_with_zero_padding(bootstrapped_db):
    first = poc_strength_data.create_run("sql_strong_doc_weak")
    second = poc_strength_data.create_run("ambiguous_signal")

    assert first["id"] == "run_0001"
    assert second["id"] == "run_0002"


def test_run_id_format_round_trips_beyond_four_digits(bootstrapped_db):
    """5桁以上になっても(`_format_run_id`が生成する形式であれば)取得できる。"""
    from caliboo_api.data.poc_strength_data import _format_run_id, _parse_run_id

    assert _parse_run_id(_format_run_id(10000)) == 10000
    assert _format_run_id(10000) == "run_10000"


def test_created_run_backfills_run_id_into_strength_output(bootstrapped_db):
    run = poc_strength_data.create_run("sql_strong_doc_weak")

    assert run["strengths"]["runId"] == run["id"]


def test_created_run_is_persisted_and_retrievable(bootstrapped_db):
    created = poc_strength_data.create_run("sql_strong_doc_weak")

    fetched = poc_strength_data.get_run_detail(created["id"])

    assert fetched == created


def test_run_list_is_newest_first(bootstrapped_db):
    poc_strength_data.create_run("sql_strong_doc_weak")
    poc_strength_data.create_run("communication_strong")

    runs = poc_strength_data.fetch_run_list()

    assert [run["id"] for run in runs] == ["run_0002", "run_0001"]
    assert "trajectory" not in runs[0]


@pytest.mark.parametrize(
    "run_id", ["run_9999", "oops", "run_abc", "run_", "0001", "run_1", "run_001", "run_00001"]
)
def test_get_run_detail_returns_none_for_unknown_or_malformed_id(bootstrapped_db, run_id):
    """非正規形式(4桁ゼロ詰めでない)は、既存の行番号と数値上一致していても404にする。"""
    poc_strength_data.create_run("sql_strong_doc_weak")

    assert poc_strength_data.get_run_detail(run_id) is None


def test_persona_options_expose_only_selection_metadata(bootstrapped_db):
    options = poc_strength_data.list_persona_options()

    assert [option["personaKey"] for option in options] == [
        script["personaKey"] for script in PERSONA_SCRIPTS
    ]
    assert all(set(option) == {"personaKey", "label", "description"} for option in options)


def test_run_pipeline_rejects_unknown_persona():
    with pytest.raises(UnknownPersonaError):
        run_pipeline("no_such_persona")


def test_pipeline_numbers_iterations_from_one():
    result = run_pipeline("sql_strong_doc_weak")

    assert [item["iteration"] for item in result["trajectory"]] == [1, 2, 3]


def test_pipeline_puts_fan_in_result_into_diary_mentor_comment():
    result = run_pipeline("sql_strong_doc_weak")

    assert result["diary"]["mentorComment"] == result["reviews"]["fanInComment"]


def test_pipeline_does_not_pass_answers_to_analysis(monkeypatch):
    """解析が`injectedPersona`を読めていないことを、値を変えても結果が変わらないことで確かめる。

    !NOTE: 差し替える値には、このペルソナでは検出されないはずのスキル(RLMT)の
           キーワードを入れる。解析はキーワード照合で判定するため、無関係な文言に
           すると「解析に混入しても結果が変わらない」ことになり、混入を検出できない
           テストになってしまう。
    """
    script = find_script("sql_strong_doc_weak")
    baseline = run_pipeline("sql_strong_doc_weak")["strengths"]["strengths"]
    assert "RLMT" not in [item["layerTask"]["skillCode"] for item in baseline]

    monkeypatch.setitem(script, "injectedPersona", "ヒアリングとすり合わせで橋渡しをする新人")
    modified = run_pipeline("sql_strong_doc_weak")["strengths"]["strengths"]

    assert modified == baseline


def test_pipeline_keeps_skill_hint_for_display_but_not_for_analysis(monkeypatch):
    """`skillHint`はレスポンスには残るが、解析の判定には影響しない。

    !NOTE: `injectedPersona`側と同じ理由で、差し替える値にはこのペルソナで検出されない
           スキル(RLMT)のキーワードを入れる。スキルコード文字列だけを入れると、
           「コードを直接参照する形の漏洩」しか検出できないため。
    """
    script = find_script("sql_strong_doc_weak")
    original_hints = [item["task"]["skillHint"] for item in script["iterations"]]
    baseline = run_pipeline("sql_strong_doc_weak")["strengths"]["strengths"]
    assert "RLMT" not in [item["layerTask"]["skillCode"] for item in baseline]

    leaked_hint = "RLMT(ヒアリングとすり合わせで橋渡しをする力)"
    for index in range(len(script["iterations"])):
        monkeypatch.setitem(script["iterations"][index]["task"], "skillHint", leaked_hint)
    result = run_pipeline("sql_strong_doc_weak")

    assert original_hints == ["DBAD", "DTAN", "DOCM"]
    assert [item["task"]["skillHint"] for item in result["trajectory"]] == [leaked_hint] * 3
    assert result["strengths"]["strengths"] == baseline


def test_authored_mock_provider_returns_script_content():
    provider = AuthoredMockProvider()
    script = find_script("sql_strong_doc_weak")

    assert provider.name == "authored_mock_v1"
    assert provider.worker_output(script, 0) == script["iterations"][0]["workerOutput"]
    assert provider.trainer_feedback(script, 2) == script["iterations"][2]["trainerFeedback"]
    assert provider.review(script, "beta")["reviewerRole"] == "講師"


def test_authored_mock_provider_copies_diary_so_callers_cannot_mutate_the_script():
    provider = AuthoredMockProvider()
    script = find_script("ambiguous_signal")

    diary = provider.diary_narrative(script)
    diary["mentorComment"] = "後から足したコメント"
    diary["tasks"][0]["what"] = "書き換え"

    assert "mentorComment" not in script["diary"]
    assert script["diary"]["tasks"][0]["what"] != "書き換え"


def test_authored_mock_provider_rejects_unknown_reviewer():
    with pytest.raises(KeyError):
        AuthoredMockProvider().review(find_script("ambiguous_signal"), "delta")


def test_find_script_returns_none_for_unknown_persona():
    assert find_script("no_such_persona") is None


@pytest.mark.parametrize("script", PERSONA_SCRIPTS, ids=lambda script: script["personaKey"])
def test_each_persona_script_meets_its_declared_expectations(script):
    """仕様書§8(a): 台本が宣言した期待(復元すべき強み・出てはいけない強み)を満たす。"""
    result = run_pipeline(script["personaKey"])["strengths"]

    all_codes = [item["layerTask"]["skillCode"] for item in result["strengths"]]
    detected = [
        item["layerTask"]["skillCode"]
        for item in result["strengths"]
        if item["status"] != "insufficient_evidence"
    ]

    for code in script["expectedSkillCodes"]:
        assert code in detected
    for code in script["expectedAbsentSkillCodes"]:
        assert code not in all_codes
    assert result["overallStatus"] == script["expectedOverallStatus"]


@pytest.mark.parametrize("script", PERSONA_SCRIPTS, ids=lambda script: script["personaKey"])
def test_each_persona_script_has_three_iterations_and_three_reviews(script):
    assert len(script["iterations"]) == 3
    assert [review["agentKey"] for review in script["reviews"]] == ["alpha", "beta", "gamma"]
    assert len(script["diary"]["tasks"]) == 3


def test_create_imported_run_backfills_run_id_into_strength_output(bootstrapped_db):
    run = poc_strength_data.create_imported_run(_minimal_import_payload())

    assert run["strengths"]["runId"] == run["id"]


def test_create_imported_run_is_persisted_and_retrievable(bootstrapped_db):
    created = poc_strength_data.create_imported_run(_minimal_import_payload())

    fetched = poc_strength_data.get_run_detail(created["id"])

    assert fetched == created


def test_import_run_produces_the_same_top_level_shape_as_script_pipeline():
    """台本経由(`run_pipeline`)・外部投入経由(`import_run`)が共通の`_assemble_run`を
    通るため、run一式のトップレベル構造(キー集合)が一致する。"""
    script_result = run_pipeline("sql_strong_doc_weak")
    import_result = import_run(_minimal_import_payload())

    assert set(import_result) == set(script_result)
    assert set(import_result["reviews"]) == set(script_result["reviews"])
    assert set(import_result["diary"]) == set(script_result["diary"])
    assert set(import_result["trace"]) >= {"generationProvider", "analysisProvider"}


def test_import_run_puts_fan_in_result_into_diary_mentor_comment():
    result = import_run(_minimal_import_payload())

    assert result["diary"]["mentorComment"] == result["reviews"]["fanInComment"]


def test_import_run_does_not_pass_injected_persona_to_analysis():
    """外部投入経路でも、`injectedPersona`は解析エンジンに渡らない(循環評価の回避)。

    !NOTE: 台本経由の同名テスト(`test_pipeline_does_not_pass_answers_to_analysis`)と同じ理由で、
           差し替える値にはこのペイロードでは検出されないスキル(RLMT)のキーワードを入れる。
    """
    baseline = import_run(_minimal_import_payload())["strengths"]["strengths"]
    assert "RLMT" not in [item["layerTask"]["skillCode"] for item in baseline]

    modified = import_run(
        _minimal_import_payload(injectedPersona="ヒアリングとすり合わせで橋渡しをする新人")
    )["strengths"]["strengths"]

    assert modified == baseline


def test_import_run_keeps_skill_hint_for_display_but_not_for_analysis():
    """`skillHint`はレスポンスの`trajectory`には残るが、解析の判定には影響しない。"""
    baseline = import_run(_minimal_import_payload())["strengths"]["strengths"]
    assert "RLMT" not in [item["layerTask"]["skillCode"] for item in baseline]

    leaked_hint_payload = _minimal_import_payload()
    for item in leaked_hint_payload["trajectory"]:
        item["task"]["skillHint"] = "RLMT(ヒアリングとすり合わせで橋渡しをする力)"
    result = import_run(leaked_hint_payload)

    assert [item["task"]["skillHint"] for item in result["trajectory"]] == [
        "RLMT(ヒアリングとすり合わせで橋渡しをする力)"
    ] * 3
    assert result["strengths"]["strengths"] == baseline
