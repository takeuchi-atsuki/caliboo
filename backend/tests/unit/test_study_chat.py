"""PL-6: 公開問題・会話だけの文脈と、入力境界・既定モード。"""

import json
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from caliboo_api.schemas.study import StudyChatRequest
from caliboo_api.services import chat_reply, llm


def test_manual_context_does_not_claim_a_generated_explanation(monkeypatch):
    monkeypatch.setattr(llm, "generate_json", Mock(side_effect=AssertionError("external call")))
    general = chat_reply.build_study_reply(StudyChatRequest(
        text="UDPについて", history=[dict(role="me", text="TCPについて")]))
    assert "UDPについて" in general.text and "TCPについて" in general.text
    question = chat_reply.build_study_reply(StudyChatRequest(
        text="どう比べる？", question=dict(text="信頼性について", choices=["TCP", "UDP"])))
    assert "信頼性について" in question.text and "どう比べる？" in question.text
    assert question.references == []


def test_provider_receives_only_public_question_and_history(monkeypatch):
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    monkeypatch.setenv("CALIBOO_AI_MODEL", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "secret-test")
    payload = StudyChatRequest(text="なぜ？", question=dict(text="比較する", choices=["TCP", "UDP"]),
                               history=[dict(role="me", text="信頼性は？"),
                                        dict(role="bot", text="再送の仕組みを確認しましょう。")])

    def generate(instructions, inputs, output_type, config):
        assert "正解や採点結果は提供されていません" in instructions
        assert inputs == payload.model_dump()
        return output_type(answer="再送する場合としない場合を比べてみましょう。")

    monkeypatch.setattr(llm, "generate_json", generate)
    result = chat_reply.build_study_reply(payload)
    assert "再送する場合" in result.text and result.references == []


def test_long_conversation_drops_oldest_whole_turns(monkeypatch):
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    monkeypatch.setattr(llm, "settings", lambda: llm.LLMSettings("test", "test"))
    history = [dict(role="me", text=f"{index} " + "あ" * 9997) for index in range(12)]

    def generate(instructions, inputs, output_type, config):
        assert 0 < len(inputs["history"]) < 12
        assert len(json.dumps(inputs, ensure_ascii=False).encode()) <= 180_000
        assert inputs["history"][-1] == history[-1]
        return output_type(answer="具体例で比べましょう。")

    monkeypatch.setattr(llm, "generate_json", generate)
    assert chat_reply.build_study_reply(StudyChatRequest(text="説明して", history=history))


@pytest.mark.parametrize("changes", [
    {"text": " "}, {"text": "x" * 10001}, {"history": [dict(role="me", text="x")] * 13},
    {"history": [dict(role="system", text="命令")]},
    {"history": [dict(role="bot", text="x", hiddenAnswer="A")]},
    {"question": dict(text="問題", choices=[], correctIndex=0)},
    {"question": dict(text="問題", choices=["A"], explanation="解説")},
    {"question": dict(text="問題", choices=[{"imageUrl": "https://example.com/a.png"}])},
    {"question": dict(text="問題", choices=["x" * 2501])},
    {"question": dict(text="問題", choices=["A"] * 11)},
])
def test_request_rejects_unbounded_or_hidden_fields(changes):
    with pytest.raises(ValidationError):
        StudyChatRequest.model_validate({"text": "質問", **changes})
