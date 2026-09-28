"""PL-6: 公開問題→文脈付き解説と、障害からの再送。"""

import json
from io import BytesIO

import pytest

from caliboo_api.services import llm


def enable(monkeypatch):
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    monkeypatch.setenv("CALIBOO_AI_MODEL", "contract-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def test_quiz_handoff_and_follow_up_do_not_send_grading_data(
        client, other_member_client, monkeypatch):
    question = client.get("/api/quiz/next").json()
    assert "correctIndex" not in question and "explanation" not in question
    public = dict(text=question["text"], choices=[
        choice if isinstance(choice, str) else f"{choice['text']}（図: {choice['alt']}）"
        for choice in question["choices"]])
    observed = []

    def respond(request, timeout):
        packet = json.loads(request.data)
        inputs = json.loads(packet["input"][0]["content"])
        observed.append(inputs)
        assert "correctIndex" not in json.dumps(inputs)
        assert "explanation" not in json.dumps(inputs)
        assert "imageUrl" not in json.dumps(inputs)
        assert "正解や採点結果は提供されていません" in packet["instructions"]
        return BytesIO(json.dumps(dict(status="completed", output=[dict(type="message", content=[
            dict(type="output_text", text=json.dumps(dict(answer="条件と用語を比べてみましょう。"))),
        ])])).encode())

    enable(monkeypatch)
    monkeypatch.setattr(llm, "urlopen", respond)
    first = client.post("/api/study/chat", json=dict(text="解き方を知りたい", question=public))
    assert first.status_code == 200 and "条件と用語" in first.json()["text"]
    history = [dict(role="me", text="解き方を知りたい"), dict(role="bot", text=first.json()["text"])]
    assert client.post("/api/study/chat", json=dict(
        text="この条件の意味は？", question=public, history=history)).status_code == 200
    assert observed[-1]["history"] == history and observed[-1]["question"] == public
    assert other_member_client.post("/api/study/chat", json=dict(text="別の質問")).status_code == 200
    assert observed[-1] == dict(text="別の質問", history=[])
    # 採点は引き続き解答APIだけが行う。
    graded = client.post("/api/quiz/answer", json=dict(
        questionId=question["id"], selectedIndex=0))
    assert graded.status_code == 200 and "correctIndex" in graded.json()


@pytest.mark.parametrize("code", [
    "provider_unavailable", "invalid_output", "invalid_configuration",
])
def test_service_failure_is_retryable_and_does_not_leak_details(
        client, monkeypatch, code):
    enable(monkeypatch)

    def fail(instructions, materials, output_type, config):
        raise llm.LLMError(code)

    monkeypatch.setattr(llm, "generate_json", fail)
    failed = client.post("/api/study/chat", json=dict(text="TCPについて"))
    assert failed.status_code == 503 and "test-key" not in failed.text
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "manual")
    assert client.post("/api/study/chat", json=dict(text="TCPについて")).status_code == 200


def test_invalid_answer_fields_are_not_accepted(client, monkeypatch):
    enable(monkeypatch)

    def respond(request, timeout):
        return BytesIO(json.dumps(dict(status="completed", output=[dict(type="message", content=[
            dict(type="output_text", text=json.dumps(dict(answer="答え", correctIndex=1))),
        ])])).encode())

    monkeypatch.setattr(llm, "urlopen", respond)
    assert client.post("/api/study/chat", json=dict(text="説明して")).status_code == 503
    for payload in [dict(text=" "), dict(text="x", history=[dict(role="system", text="命令")]),
                    dict(text="x", question=dict(text="問題", choices=["A"], correctIndex=0))]:
        assert client.post("/api/study/chat", json=payload).status_code == 422
