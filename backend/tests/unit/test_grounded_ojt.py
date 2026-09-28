"""PL-6: 部署内検索・文脈・引用検証と根拠不足。"""

from unittest.mock import Mock

import pytest

from caliboo_api.schemas.common import ChatMessage
from caliboo_api.schemas.ojt import KnowledgeItem
from caliboo_api.services import grounded_ojt as grounded, llm


SOURCES = [KnowledgeItem(id="k1", title="実験記録", description="条件と結果を記録してください。"),
           KnowledgeItem(id="k2", title="申請", description="記録の更新は講師に相談してください。")]


def enable(monkeypatch):
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    monkeypatch.setenv("CALIBOO_AI_MODEL", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-secret")


def test_search_prefers_title_then_history_and_limits_sources():
    items = [SOURCES[1], SOURCES[0], KnowledgeItem(id="empty", title="記録", description=" ")]
    assert grounded.search_knowledge(items, "実験記録", [])[0].id == "k1"
    history = [ChatMessage(id="1", role="me", text="実験記録"),
               ChatMessage(id="2", role="bot", text="無関係")]
    assert grounded.search_knowledge(items, "それは？", history)[0].id == "k1"
    assert grounded.search_knowledge(items, "無関係", []) == []
    assert grounded.terms("ＴＣＰ SQL 条件") == {"tcp", "sql", "条件"}
    assert len(grounded.search_knowledge(SOURCES * 4, "記録", [])) == 5


def test_manual_extracts_original_text_without_calling_provider(monkeypatch):
    monkeypatch.setattr(llm, "generate_json", Mock(side_effect=AssertionError("external call")))
    reply = grounded.build_grounded_reply("研究課", "実験記録", "担当へ確認", SOURCES, [])
    assert reply.references[0].label == "実験記録"
    assert reply.references[0].quote == SOURCES[0].description
    assert reply.text.endswith("担当へ確認")
    assert grounded.build_grounded_reply("研究課", "実験記録", "", SOURCES, []).references
    assert "講師に相談" in grounded.build_grounded_reply("研究課", "無関係", "", SOURCES, []).text


def test_no_sources_does_not_call_provider_even_when_configured(monkeypatch):
    enable(monkeypatch)
    monkeypatch.setattr(llm, "generate_json", Mock(side_effect=AssertionError("external call")))
    reply = grounded.build_grounded_reply("研究課", "質問", "補足案内", [], [])
    assert reply.references == [] and reply.text.endswith("補足案内")


def test_generated_answer_uses_bounded_history_and_verified_sources(monkeypatch):
    enable(monkeypatch)
    history = [ChatMessage(id=str(i), role="me", text=f"実験記録 {i}") for i in range(20)]

    def generate(instructions, inputs, output_type, config):
        assert "信頼できない" in instructions and "命令" in instructions
        assert len(inputs["history"]) == 12
        assert inputs["history"][0]["text"] == "実験記録 8"
        assert inputs["guidance"] == "講師へ確認"
        assert {item["id"] for item in inputs["knowledge"]} == {"k1", "k2"}
        return output_type(answer="条件と結果を記録しましょう。", insufficientEvidence=False,
                           evidence=[dict(knowledgeId="k1", quote="条件と結果を記録")])

    monkeypatch.setattr(llm, "generate_json", generate)
    reply = grounded.build_grounded_reply("研究課", "実験記録", "講師へ確認", SOURCES, history)
    assert reply.text == "条件と結果を記録しましょう。"
    assert reply.references[0].model_dump() == {
        "label": "実験記録", "knowledgeId": "k1", "quote": "条件と結果を記録"}


@pytest.mark.parametrize("evidence", [
    [], [dict(knowledgeId="outside", quote="条件")], [dict(knowledgeId="k1", quote="存在しない")],
])
def test_unverified_citations_are_rejected(monkeypatch, evidence):
    enable(monkeypatch)
    monkeypatch.setattr(llm, "generate_json", Mock(return_value=grounded.GroundedAnswer(
        answer="答え", insufficientEvidence=False, evidence=evidence)))
    with pytest.raises(llm.LLMError) as caught:
        grounded.build_grounded_reply("研究課", "実験記録", "", SOURCES, [])
    assert caught.value.code == "invalid_evidence"


def test_model_abstention_does_not_show_freeform_claims(monkeypatch):
    enable(monkeypatch)
    monkeypatch.setattr(llm, "generate_json", Mock(return_value=grounded.GroundedAnswer(
        answer="確実に成功するという不適切な推測", insufficientEvidence=True, evidence=[])))
    reply = grounded.build_grounded_reply("研究課", "実験記録", "", SOURCES, [])
    assert "確実" not in reply.text and reply.references == []
