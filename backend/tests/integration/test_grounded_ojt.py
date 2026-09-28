"""PL-6: 部署根拠・本人会話・障害復旧と講師相談。"""

import json
from io import BytesIO

import pytest

from caliboo_api.db import session_scope
from caliboo_api.extension_models import AccountState
from caliboo_api.services import grounded_ojt, llm


def configure(admin_client, dept_id, title, description):
    return admin_client.post("/api/ojt/departments", json=dict(
        id=dept_id, name=f"{dept_id}課", icon="ph ph-code", color="#d6ebff",
        welcomeMessage="ご案内", quickAsks=["実験記録"], replyGuidance="原文を確認してください。",
        knowledge=[dict(title=title, description=description)],
    )).json()


def enable(monkeypatch):
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    monkeypatch.setenv("CALIBOO_AI_MODEL", "contract-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def test_grounded_history_and_department_boundaries(client, admin_client, other_member_client,
                                                    monkeypatch):
    configure(admin_client, "research", "実験記録", "条件と結果を記録する。")
    configure(admin_client, "restricted", "実験記録", "他部署だけの秘密の手順。")
    endpoint = "/api/ojt/chat"
    assert other_member_client.post(endpoint, json={
        "deptId": "research", "text": "他人の実験記録"}).status_code == 200
    assert client.post(endpoint, json={
        "deptId": "research", "text": "自分の実験記録"}).status_code == 200
    seen = []

    def respond(request, timeout):
        packet = json.loads(request.data)
        inputs = json.loads(packet["input"][0]["content"])
        seen.append(inputs)
        assert "他部署だけ" not in json.dumps(inputs, ensure_ascii=False)
        assert "他人の実験記録" not in json.dumps(inputs, ensure_ascii=False)
        assert inputs["history"][0]["text"] == "自分の実験記録"
        output = dict(answer="条件と結果を残し、講師へ確認してください。", insufficientEvidence=False,
                      evidence=[dict(knowledgeId="k1", quote="条件と結果を記録")])
        return BytesIO(json.dumps(dict(status="completed", output=[dict(type="message", content=[
            dict(type="output_text", text=json.dumps(output)),
        ])])).encode())

    enable(monkeypatch)
    monkeypatch.setattr(llm, "urlopen", respond)
    result = client.post(endpoint, json={"deptId": "research", "text": "それはどのように？"})
    assert result.status_code == 200
    assert result.json()["references"] == [dict(
        knowledgeId="k1", label="実験記録", quote="条件と結果を記録")]
    history = client.get("/api/ojt/departments/research/messages").json()["messages"]
    assert len(history) == 5 and history[-1] == result.json()
    assert len(seen) == 1
    assert client.post("/api/ojt/departments/research/escalate").status_code == 200
    thread = admin_client.get("/api/ojt/escalations").json()["threads"][0]
    assert thread["messages"][-1]["references"] == result.json()["references"]
    assert admin_client.post(f"/api/ojt/escalations/{thread['id']}/reply", json={
        "text": "指定の様式を使ってください。"}).status_code == 200


@pytest.mark.parametrize("code", ["provider_unavailable", "invalid_output", "invalid_evidence"])
def test_failed_turn_is_not_saved_and_retry_saves_once(client, admin_client, monkeypatch, code):
    configure(admin_client, "research", "実験記録", "条件と結果を記録する。")
    enable(monkeypatch)

    def fail(instructions, materials, output_type, config):
        raise llm.LLMError(code)

    monkeypatch.setattr(llm, "generate_json", fail)
    payload = {"deptId": "research", "text": "実験記録の手順は？"}
    result = client.post("/api/ojt/chat", json=payload)
    assert result.status_code == 503 and "test-key" not in result.text
    assert len(client.get("/api/ojt/departments/research/messages").json()["messages"]) == 1
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "manual")
    assert client.post("/api/ojt/chat", json=payload).status_code == 200
    assert len(client.get("/api/ojt/departments/research/messages").json()["messages"]) == 3


@pytest.mark.parametrize("change", ["configuration", "inactive"])
def test_changes_during_inference_prevent_stale_save(client, admin_client, monkeypatch, change):
    configuration = configure(admin_client, "research", "実験記録", "条件と結果を記録する。")
    user_id = client.get("/api/auth/me").json()["id"]
    enable(monkeypatch)

    def generate(instructions, materials, output_type, config):
        if change == "configuration":
            update = {key: value for key, value in configuration.items() if key != "id"}
            update["knowledge"] = []
            response = admin_client.post("/api/ojt/departments/research/configuration", json=update)
            assert response.status_code == 200
        else:
            with session_scope() as session:
                session.get(AccountState, user_id).active = False
                session.commit()
        return grounded_ojt.GroundedAnswer(
            answer="条件を記録する。", insufficientEvidence=False,
            evidence=[dict(knowledgeId="k1", quote="条件と結果を記録する。")])

    monkeypatch.setattr(llm, "generate_json", generate)
    result = client.post("/api/ojt/chat", json={"deptId": "research", "text": "実験記録"})
    assert result.status_code == (409 if change == "configuration" else 403)
    if change == "inactive":
        with session_scope() as session:
            session.get(AccountState, user_id).active = True
            session.commit()
        client.post("/api/auth/login", json={"loginId": "yuki", "password": "caliboo-yuki"})
    assert len(client.get("/api/ojt/departments/research/messages").json()["messages"]) == 1
