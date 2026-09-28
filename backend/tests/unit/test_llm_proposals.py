"""PL-4/5: 課題案の材料・引用検証と既存providerの切替。"""

import pytest

from caliboo_api.services import llm
from caliboo_api.services.assignment_proposal import pipeline
from caliboo_api.services.assignment_proposal.llm_provider import (
    GeneratedProposal, LLMProposalGenerator,
)
from caliboo_api.services.assignment_proposal.theme_catalog import FALLBACK_THEME_KEY


@pytest.fixture()
def proposal_inputs():
    return dict(member_name="送信しない個人名", reports=[dict(
        date="2026-09-29", keep="テストの境界値を発見した。", problem="説明が難しい。",
        try_="", mood=[], moodComment="")], submission_statuses=["not_submitted", "reviewed"],
        feedbacks=[dict(date="2026-09-29", comment="観点の理由を説明しましょう。")], excluded_themes=set())


def generated(**changes):
    return GeneratedProposal(**{**dict(
        themeKey=FALLBACK_THEME_KEY, title="根拠を説明する練習", body="観点を2つ挙げ、理由を書く。",
        messageForMember="次の共有会で試してみましょう。", aim="説明力を伸ばす", rationale="説明に難しさがあるため。",
        estimateMinutes=15, evidence=[dict(materialId="material:0", quote="説明が難しい。")],
    ), **changes})


def test_llm_uses_progress_and_sources_without_identity(monkeypatch, proposal_inputs):
    proposal_inputs["reports"][0]["try"] = proposal_inputs["reports"][0].pop("try_")

    def generate(instructions, materials, output_type, config):
        assert "信頼できない" in instructions
        assert proposal_inputs["member_name"] not in str(materials)
        assert materials["progress"]["notSubmittedCount"] == 1
        assert materials["progress"]["reviewedCount"] == 1
        assert any(source["kind"] == "feedback" for source in materials["sources"])
        return generated()
    monkeypatch.setattr(llm, "generate_json", generate)
    provider = LLMProposalGenerator(llm.LLMSettings("model", "secret"))
    result = provider.generate(**proposal_inputs)
    assert result["materials"] == [dict(kind="report", date="2026-09-29",
                                        sourceLabel="日報 Problem", quote="説明が難しい。")]
    assert provider.name.startswith("openai:model:")


@pytest.mark.parametrize("changes,code", [
    ({"themeKey": "invented"}, "invalid_theme"),
    ({"evidence": [dict(materialId="unknown", quote="説明が難しい。")]}, "invalid_evidence"),
    ({"evidence": [dict(materialId="material:0", quote="存在しない根拠")]}, "invalid_evidence"),
])
def test_invalid_theme_or_quote_cannot_be_saved(monkeypatch, proposal_inputs, changes, code):
    proposal_inputs["reports"][0]["try"] = proposal_inputs["reports"][0].pop("try_")
    monkeypatch.setattr(llm, "generate_json", lambda *args: generated(**changes))
    with pytest.raises(llm.LLMError, match=code):
        LLMProposalGenerator(llm.LLMSettings("model", "secret")).generate(**proposal_inputs)


def test_empty_materials_rejected_and_provider_switch(monkeypatch):
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "manual")
    assert pipeline.generator_name() == "rule_based_v1"
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    monkeypatch.setenv("CALIBOO_AI_MODEL", "model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    assert pipeline.generator_name().startswith("openai:model:")
    with pytest.raises(llm.LLMError, match="insufficient_materials"):
        pipeline.generate_proposal(member_name="名前", reports=[], feedbacks=[],
                                   submission_statuses=[], excluded_themes=set())


def test_concurrent_generation_has_only_one_pending_proposal(user_ids, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from caliboo_api.data import assignment_proposal_data as data
    from caliboo_api.db import session_scope
    from caliboo_api.models import User

    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "manual")
    user_id = user_ids["yuki"]
    with session_scope() as session:
        output = data._run_generator(session, session.get(User, user_id))
    barrier = Barrier(2)

    def generate(session, target_user):
        barrier.wait(timeout=5)
        return output

    monkeypatch.setattr(data, "_run_generator", generate)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(data.create_or_get_pending_proposal, user_id) for _index in range(2)]
        first, second = [future.result(timeout=10) for future in futures]
    assert first[0].id == second[0].id
    assert sorted([first[1], second[1]]) == [False, True]


def test_recent_feedback_limit_and_excluded_themes(monkeypatch, proposal_inputs):
    from caliboo_api.services.assignment_proposal.theme_catalog import THEME_CATALOG

    proposal_inputs["reports"][0]["try"] = proposal_inputs["reports"][0].pop("try_")
    proposal_inputs["feedbacks"] = [dict(date="2026-09-29", comment=f"観測{index}")
                                    for index in range(30)]
    proposal_inputs["excluded_themes"] = {theme.key for theme in THEME_CATALOG}

    def generate(instructions, materials, output_type, config):
        assert materials["allowedThemes"] == [FALLBACK_THEME_KEY]
        feedbacks = [source["text"] for source in materials["sources"]
                     if source["kind"] == "feedback"]
        assert feedbacks == [f"観測{index}" for index in range(10, 30)]
        return generated()

    monkeypatch.setattr(llm, "generate_json", generate)
    LLMProposalGenerator(llm.LLMSettings("model", "secret")).generate(**proposal_inputs)
