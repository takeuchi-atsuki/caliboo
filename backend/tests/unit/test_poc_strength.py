"""強み解析PoCのAPI仕様レベルのテスト(docs/screens/strengths.md・docs/api.mdに対応)。"""

QUADRANTS = {
    "High Will / High Skill",
    "High Will / Low Skill",
    "Low Will / High Skill",
    "Low Will / Low Skill",
}


def _create_run(client, persona_key="sql_strong_doc_weak"):
    response = client.post("/api/poc/runs", json={"personaKey": persona_key})
    assert response.status_code == 200
    return response.json()


def _strength_by_code(run, skill_code):
    for item in run["strengths"]["strengths"]:
        if item["layerTask"]["skillCode"] == skill_code:
            return item
    return None


def _import_payload(**overrides):
    """POST /api/poc/runs/import 用のサンプルペイロード。

    軌跡(iteration1)・日報・レビュー(alpha)それぞれにDBADのキーワード
    (「SQL」「クエリ」「テーブル」「結合」「インデックス」)を1件以上含め、
    3種類の裏付けが揃って`confirmed`になる構成にしている(既存の台本と同じ組み立て方)。
    """
    payload = {
        "subjectId": "emp_101",
        "label": "Claude生成run(SQLが強い新人)",
        "injectedPersona": "SQL/データ処理が強い新人",
        "trajectory": [
            {
                "iteration": 1,
                "task": {
                    "taskId": "ext_1",
                    "title": "受注データの集計",
                    "description": "受注データを集計してください。",
                    "skillHint": "DBAD",
                },
                "workerOutput": (
                    "SQLクエリを作成し、ordersテーブルとorder_itemsテーブルを"
                    "結合して月次の集計を行いました。"
                ),
                "trainerFeedback": "良い進め方です。次はダッシュボード化してみましょう。",
            },
            {
                "iteration": 2,
                "task": {
                    "taskId": "ext_2",
                    "title": "集計結果の可視化",
                    "description": "集計結果を可視化してください。",
                    "skillHint": "DTAN",
                },
                "workerOutput": "インデックスを追加してクエリの速度を改善しました。",
                "trainerFeedback": "性能を自分で切り分けられている点が良いです。",
            },
            {
                "iteration": 3,
                "task": {
                    "taskId": "ext_3",
                    "title": "引き継ぎメモの作成",
                    "description": "引き継ぎメモを作成してください。",
                    "skillHint": "DOCM",
                },
                "workerOutput": "引き継ぎメモをまとめました。",
                "trainerFeedback": "次は前提の説明を厚くしましょう。",
            },
        ],
        "diary": {
            "date": "2026-09-24",
            "tasks": [
                {
                    "time": "09:30-12:00",
                    "what": "受注データの集計クエリ作成",
                    "progressDesc": "SQLクエリを作成し検算まで実施",
                    "progressRate": 100,
                },
            ],
            "feelings": {
                "emotion": "たのしい",
                "trigger": "クエリが想定通り動いたとき",
                "nextAction": "次は可視化に着手する",
            },
            "kpt": {
                "keep": "検算してから提出する進め方を続けたい",
                "problem": "引き継ぎ資料の分量が不足している",
                "try": "初めて読む人のつもりで読み返す",
            },
        },
        "reviews": [
            {
                "agentKey": "alpha",
                "reviewerRole": "管理職",
                "magiTone": "MELCHIOR",
                "comment": "集計クエリの構成が後から見ても分かりやすい。",
                "flags": [],
            },
            {
                "agentKey": "beta",
                "reviewerRole": "講師",
                "magiTone": "BALTHASAR",
                "comment": "前回の助言を素直に反映できている。",
                "flags": [],
            },
            {
                "agentKey": "gamma",
                "reviewerRole": "シニアエンジニア",
                "magiTone": "CASPER",
                "comment": "インデックスの追加判断に地力がある。",
                "flags": [],
            },
        ],
        "trace": {
            "generationProvider": "claude_session",
            "agents": [
                {"key": "strength-worker", "model": "sonnet", "promptVersion": "2026-09-24.1"},
                {"key": "strength-trainer", "model": "sonnet", "promptVersion": "2026-09-24.1"},
                {"key": "strength-reviewer", "model": "sonnet", "promptVersion": "2026-09-24.1"},
            ],
        },
    }
    payload.update(overrides)
    return payload


def _import_run(client, **overrides):
    return client.post("/api/poc/runs/import", json=_import_payload(**overrides))


def test_persona_list_returns_three_demo_scenarios(client):
    response = client.get("/api/poc/personas")

    assert response.status_code == 200
    personas = response.json()["personas"]
    assert [persona["personaKey"] for persona in personas] == [
        "sql_strong_doc_weak",
        "ambiguous_signal",
        "communication_strong",
    ]
    assert all(persona["label"] and persona["description"] for persona in personas)


def test_create_run_returns_completed_run_with_all_pipeline_outputs(client):
    run = _create_run(client)

    assert run["id"] == "run_0001"
    assert run["status"] == "completed"
    assert run["subjectId"] == "emp_001"
    assert len(run["trajectory"]) == 3
    assert [item["iteration"] for item in run["trajectory"]] == [1, 2, 3]
    assert all(item["workerOutput"] and item["trainerFeedback"] for item in run["trajectory"])
    assert len(run["reviews"]["reviews"]) == 3
    assert run["strengths"]["runId"] == "run_0001"


def test_diary_follows_section_a_format(client):
    diary = _create_run(client)["diary"]

    assert diary["date"]
    assert len(diary["tasks"]) == 3
    assert all(
        task["time"] and task["what"] and task["progressDesc"] and task["progressRate"] >= 0
        for task in diary["tasks"]
    )
    assert diary["feelings"]["emotion"] and diary["feelings"]["trigger"]
    assert diary["feelings"]["nextAction"]
    assert diary["kpt"]["keep"] and diary["kpt"]["problem"] and diary["kpt"]["try"]


def test_diary_mentor_comment_holds_fan_in_result(client):
    run = _create_run(client)

    assert run["diary"]["mentorComment"] == run["reviews"]["fanInComment"]
    assert "管理職" in run["diary"]["mentorComment"]
    assert "講師" in run["diary"]["mentorComment"]
    assert "シニアエンジニア" in run["diary"]["mentorComment"]


def test_injected_known_persona_is_reproduced_as_confirmed_strength(client):
    """仕様書§8(a) 機構妥当性: 注入した既知の強みを解析が復元できる。"""
    run = _create_run(client, "sql_strong_doc_weak")

    database_skill = _strength_by_code(run, "DBAD")
    assert database_skill is not None
    assert database_skill["status"] == "confirmed"
    assert database_skill["confidence"] == 0.85
    assert run["strengths"]["overallStatus"] == "partial"


def test_weak_documentation_is_not_reported_as_strength(client):
    """ドキュメントが弱いペルソナで、DOCMが強みとして付与されない。"""
    run = _create_run(client, "sql_strong_doc_weak")

    assert _strength_by_code(run, "DOCM") is None


def test_ambiguous_persona_holds_back_every_judgement(client):
    """仕様書§9 過剰付与の抑制: 信号が弱いときは断定しない。"""
    run = _create_run(client, "ambiguous_signal")

    strengths = run["strengths"]["strengths"]
    assert strengths
    assert all(item["status"] == "insufficient_evidence" for item in strengths)
    assert run["strengths"]["overallStatus"] == "insufficient"
    assert run["strengths"]["notes"] == "根拠が不足するため、断定できる強みは無いと判断した"


def test_communication_persona_does_not_trigger_data_skills(client):
    """誤検出の抑制: 分野が違う強みを取り違えない。"""
    run = _create_run(client, "communication_strong")

    communication = _strength_by_code(run, "RLMT")
    assert communication is not None
    assert communication["status"] == "confirmed"
    assert _strength_by_code(run, "DBAD") is None
    assert _strength_by_code(run, "DTAN") is None
    assert run["strengths"]["overallStatus"] == "complete"


def test_support_count_determines_status_and_confidence(client):
    """根拠の種類数(軌跡/日報/レビュー)が確信度とステータスを決める。"""
    run = _create_run(client, "sql_strong_doc_weak")

    assert run["strengths"]["strengths"]
    for item in run["strengths"]["strengths"]:
        kinds = {evidence["source"]["kind"] for evidence in item["evidence"]}
        if item["status"] == "confirmed":
            assert len(kinds) == 3 and item["confidence"] == 0.85
        elif item["status"] == "tentative":
            assert len(kinds) == 2 and item["confidence"] == 0.6
        else:
            assert len(kinds) == 1 and item["confidence"] == 0.35


def test_held_back_strength_has_neither_quadrant_nor_growth_action(client):
    """根拠不足の強みは象限も育成アクションも出さない(断定していないものから次の一手を出さない)。"""
    run = _create_run(client, "ambiguous_signal")

    assert run["strengths"]["strengths"]
    for item in run["strengths"]["strengths"]:
        assert item["status"] == "insufficient_evidence"
        assert item["layerWillSkill"] is None
        assert item["growthContent"] is None


def test_confirmed_strength_carries_growth_action(client):
    """基本仕様書§7: skill_codeとWill-Skill象限の組で育成アクションを出し分ける。

    !NOTE: 象限の値そのものは台本のキーワード数で変わりうるため、ここでは固定しない
           (象限の判定ルールは`test_poc_strength_analysis_impl.py`が台本非依存で担保する)。
    """
    database_skill = _strength_by_code(_create_run(client), "DBAD")

    assert database_skill["status"] == "confirmed"
    assert database_skill["layerWillSkill"]["quadrant"] in QUADRANTS
    assert database_skill["layerWillSkill"]["policy"]
    assert database_skill["growthContent"]["contentTag"] == "sql-drill"


def test_evidence_quotes_come_from_actual_records(client):
    """根拠が実際の軌跡・日報・レビュー本文からの引用になっている。"""
    run = _create_run(client)
    database_skill = _strength_by_code(run, "DBAD")

    sources_by_kind = {
        evidence["source"]["kind"]: evidence for evidence in database_skill["evidence"]
    }
    assert set(sources_by_kind) == {"trajectory", "diary", "review"}

    trajectory_quote = sources_by_kind["trajectory"]["quote"]
    assert any(trajectory_quote in item["workerOutput"] for item in run["trajectory"])

    diary_quote = sources_by_kind["diary"]["quote"]
    diary_texts = [task["what"] for task in run["diary"]["tasks"]] + [
        run["diary"]["kpt"]["keep"],
        run["diary"]["kpt"]["problem"],
        run["diary"]["kpt"]["try"],
    ]
    assert any(diary_quote in text for text in diary_texts)

    review_evidence = sources_by_kind["review"]
    assert review_evidence["source"]["role"] in {"alpha", "beta", "gamma"}
    assert any(
        review_evidence["quote"] in review["comment"] for review in run["reviews"]["reviews"]
    )


def test_every_evidence_carries_a_quote_and_a_source(client):
    run = _create_run(client)

    assert run["strengths"]["strengths"]
    for item in run["strengths"]["strengths"]:
        assert item["evidence"]
        for evidence in item["evidence"]:
            assert evidence["quote"]
            assert evidence["source"]["field"]
            if evidence["source"]["kind"] == "trajectory":
                assert evidence["source"]["iteration"] in {1, 2, 3}
                assert evidence["source"]["role"] is None
            else:
                assert evidence["source"]["iteration"] is None


def test_reviews_cover_three_roles_with_magi_tones(client):
    reviews = _create_run(client)["reviews"]

    assert [review["agentKey"] for review in reviews["reviews"]] == ["alpha", "beta", "gamma"]
    assert [review["reviewerRole"] for review in reviews["reviews"]] == [
        "管理職",
        "講師",
        "シニアエンジニア",
    ]
    assert [review["magiTone"] for review in reviews["reviews"]] == [
        "MELCHIOR",
        "BALTHASAR",
        "CASPER",
    ]
    assert reviews["fanInFlags"] == ["属人化リスク", "引き継ぎ資料の補強が必要"]


def test_evidence_prefers_worker_output_over_task_definition(client):
    """課題文ではなく本人の成果物を優先して根拠に引用する。"""
    run = _create_run(client)
    database_skill = _strength_by_code(run, "DBAD")

    trajectory_evidence = next(
        evidence
        for evidence in database_skill["evidence"]
        if evidence["source"]["kind"] == "trajectory"
    )
    assert trajectory_evidence["source"]["field"] == "workerOutput"


def test_learning_agility_is_reported_for_every_strength(client):
    run = _create_run(client)

    for item in run["strengths"]["strengths"]:
        assert item["learningAgility"]["delta"] in {"+", "0", "-"}
        assert item["learningAgility"]["note"]


def test_same_persona_produces_identical_analysis(client):
    """決定論性: 同じペルソナなら生成日時とrun ID以外は一致する。"""
    first = _create_run(client)["strengths"]
    second = _create_run(client)["strengths"]

    for output in (first, second):
        output.pop("generatedAt")
        output.pop("runId")
    assert first == second


def test_run_list_returns_newest_first(client):
    _create_run(client, "sql_strong_doc_weak")
    _create_run(client, "communication_strong")

    runs = client.get("/api/poc/runs").json()["runs"]

    assert [run["id"] for run in runs] == ["run_0002", "run_0001"]
    assert runs[0]["personaKey"] == "communication_strong"
    assert runs[0]["status"] == "completed"


def test_run_detail_and_part_endpoints_return_matching_content(client):
    created = _create_run(client)
    run_id = created["id"]

    detail = client.get(f"/api/poc/runs/{run_id}").json()
    diary = client.get(f"/api/poc/runs/{run_id}/diary").json()
    reviews = client.get(f"/api/poc/runs/{run_id}/reviews").json()
    strengths = client.get(f"/api/poc/runs/{run_id}/strengths").json()

    assert detail == created
    assert diary == created["diary"]
    assert reviews == created["reviews"]
    assert strengths == created["strengths"]


def test_run_records_which_implementation_produced_it(client):
    """仕様書§6 トレーサビリティ: どの実装が出した結果かを後から追える。

    `agents`・`externalAnalysis`は外部投入run(`POST /api/poc/runs/import`)専用の
    フィールドのため、台本経由のrunでは常にNoneになる(`test_import_run_*`参照)。
    """
    trace = _create_run(client)["trace"]

    assert trace == {
        "generationProvider": "authored_mock_v1",
        "analysisProvider": "rule_based_v1",
        "scriptVersion": "2026-09-24",
        "agents": None,
        "externalAnalysis": None,
    }


def test_injected_persona_is_exposed_for_display_only(client):
    known = _create_run(client, "sql_strong_doc_weak")
    unknown = _create_run(client, "ambiguous_signal")

    assert known["injectedPersona"] == "SQL/データ処理が強くドキュメントが弱い新人"
    assert unknown["injectedPersona"] is None


def test_unknown_run_id_returns_404(client):
    assert client.get("/api/poc/runs/run_9999").status_code == 404
    assert client.get("/api/poc/runs/run_9999/diary").status_code == 404
    assert client.get("/api/poc/runs/run_9999/reviews").status_code == 404
    assert client.get("/api/poc/runs/run_9999/strengths").status_code == 404


def test_malformed_run_id_returns_404(client):
    assert client.get("/api/poc/runs/oops").status_code == 404
    assert client.get("/api/poc/runs/run_abc").status_code == 404


def test_unknown_persona_key_returns_404(client):
    response = client.post("/api/poc/runs", json={"personaKey": "unknown_persona"})

    assert response.status_code == 404


# --- POST /api/poc/runs/import (外部(Claude Codeセッション等)投入経路) ---


def test_import_run_returns_completed_run_with_fan_in_and_analysis(client):
    """外部投入runも台本経由と同じFan-in統合・解析(`_assemble_run`)を通る。"""
    run = _import_run(client).json()

    assert run["status"] == "completed"
    assert run["subjectId"] == "emp_101"
    assert run["personaKey"] == "external_claude"
    assert run["diary"]["mentorComment"] == run["reviews"]["fanInComment"]

    database_skill = _strength_by_code(run, "DBAD")
    assert database_skill is not None
    assert database_skill["status"] == "confirmed"
    assert {evidence["source"]["kind"] for evidence in database_skill["evidence"]} == {
        "trajectory",
        "diary",
        "review",
    }


def test_import_run_records_generation_trace(client):
    """仕様書§6トレーサビリティ: 外部投入runは台本の`scriptVersion`の代わりに`agents`を持つ。"""
    run = _import_run(client).json()

    trace = run["trace"]
    assert trace["generationProvider"] == "claude_session"
    assert trace["analysisProvider"] == "rule_based_v1"
    assert trace["scriptVersion"] is None
    assert [agent["key"] for agent in trace["agents"]] == [
        "strength-worker",
        "strength-trainer",
        "strength-reviewer",
    ]
    assert trace["externalAnalysis"] is None


def test_import_run_stores_external_strengths_when_provided(client):
    """仕様書§2「評価者の分離」: 別モデルの解析エージェント結果は`trace.externalAnalysis`に
    格納され、ルールベース解析(`strengths`)とは独立に保持される。"""
    external_strengths = {
        "subjectId": "emp_101",
        "runId": "",
        "generatedAt": "2026-09-24T00:00:00+00:00",
        "provider": "strength-analyst_opus_2026-09-24.1",
        "strengths": [],
        "overallStatus": "insufficient",
        "notes": "別モデルによる独立解析の結果",
    }

    run = _import_run(client, externalStrengths=external_strengths).json()

    stored = run["trace"]["externalAnalysis"]
    assert stored["provider"] == "strength-analyst_opus_2026-09-24.1"
    assert stored["overallStatus"] == "insufficient"
    # ルールベース解析(strengths)は独立して実行されているため、providerが異なる。
    assert run["strengths"]["provider"] == "rule_based_v1"


def test_import_run_stores_human_override_for_hitl(client):
    """仕様書§2別案(HITL): 人間が上書きした周だけ`humanOverride`が入る。"""
    payload = _import_payload()
    payload["trajectory"][0]["humanOverride"] = "人間が上書きしたフィードバック"

    run = client.post("/api/poc/runs/import", json=payload).json()

    assert run["trajectory"][0]["humanOverride"] == "人間が上書きしたフィードバック"
    assert run["trajectory"][1]["humanOverride"] is None


def test_import_run_defaults_persona_key_when_omitted(client):
    run = _import_run(client).json()

    assert run["personaKey"] == "external_claude"


def test_import_run_rejects_wrong_trajectory_length(client):
    payload = _import_payload()
    payload["trajectory"] = payload["trajectory"][:2]

    assert client.post("/api/poc/runs/import", json=payload).status_code == 422


def test_import_run_rejects_non_sequential_iterations(client):
    payload = _import_payload()
    payload["trajectory"][1]["iteration"] = 3
    payload["trajectory"][2]["iteration"] = 2

    assert client.post("/api/poc/runs/import", json=payload).status_code == 422


def test_import_run_rejects_missing_reviewer_role(client):
    payload = _import_payload()
    payload["reviews"] = payload["reviews"][:2]

    assert client.post("/api/poc/runs/import", json=payload).status_code == 422


def test_import_run_rejects_duplicate_reviewer_role(client):
    payload = _import_payload()
    payload["reviews"][2]["agentKey"] = "alpha"

    assert client.post("/api/poc/runs/import", json=payload).status_code == 422


def test_import_run_rejects_empty_diary_tasks(client):
    payload = _import_payload()
    payload["diary"]["tasks"] = []

    assert client.post("/api/poc/runs/import", json=payload).status_code == 422


def test_import_run_rejects_blank_subject_id(client):
    payload = _import_payload()
    payload["subjectId"] = "   "

    assert client.post("/api/poc/runs/import", json=payload).status_code == 422


def test_import_run_rejects_blank_trajectory_worker_output(client):
    payload = _import_payload()
    payload["trajectory"][0]["workerOutput"] = "   "

    assert client.post("/api/poc/runs/import", json=payload).status_code == 422


def test_import_run_rejects_blank_diary_task_field(client):
    payload = _import_payload()
    payload["diary"]["tasks"][0]["what"] = ""

    assert client.post("/api/poc/runs/import", json=payload).status_code == 422


def test_import_run_rejects_blank_review_comment(client):
    payload = _import_payload()
    payload["reviews"][0]["comment"] = "   "

    assert client.post("/api/poc/runs/import", json=payload).status_code == 422


def test_required_reviewer_keys_matches_fan_in_reviewer_labels():
    """schemas側で複製している`_REQUIRED_REVIEWER_KEYS`が、Fan-inのラベル集合
    (`fan_in.REVIEWER_LABELS`)と食い違っていないことを検知する。"""
    from caliboo_api.schemas.poc_strength import _REQUIRED_REVIEWER_KEYS
    from caliboo_api.services.poc_strength.fan_in import REVIEWER_LABELS

    assert _REQUIRED_REVIEWER_KEYS == frozenset(REVIEWER_LABELS)


def test_import_run_appears_ahead_of_earlier_script_run(client):
    script_run = _create_run(client)
    imported = _import_run(client).json()

    runs = client.get("/api/poc/runs").json()["runs"]

    assert [run["id"] for run in runs] == [imported["id"], script_run["id"]]
    assert runs[0]["personaKey"] == "external_claude"


def test_import_run_detail_and_part_endpoints_return_matching_content(client):
    created = _import_run(client).json()
    run_id = created["id"]

    assert client.get(f"/api/poc/runs/{run_id}").json() == created
    assert client.get(f"/api/poc/runs/{run_id}/diary").json() == created["diary"]
    assert client.get(f"/api/poc/runs/{run_id}/reviews").json() == created["reviews"]
    assert client.get(f"/api/poc/runs/{run_id}/strengths").json() == created["strengths"]
