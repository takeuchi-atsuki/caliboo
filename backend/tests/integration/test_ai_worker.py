"""PL-4/5: 実際のlifespanワーカーで、三種の入力から講師承認と本人の行動へ。"""

import json
import time
from io import BytesIO
from threading import Event

import pytest
from fastapi.testclient import TestClient

from caliboo_api.db import session_scope
from caliboo_api.extension_models import AgentJob, AgentJobExecution
from caliboo_api.main import app
from caliboo_api.services import llm
from caliboo_api.services.ai_worker import process_next
from caliboo_api.services.assignment_proposal.theme_catalog import FALLBACK_THEME_KEY


def response_packet(output):
    return BytesIO(json.dumps(dict(status="completed", output=[dict(type="message", content=[
        dict(type="output_text", text=json.dumps(output)),
    ])])).encode())


def test_automatic_learning_cycle(tmp_path, monkeypatch):
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    monkeypatch.setenv("CALIBOO_AI_MODEL", "contract-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("CALIBOO_SQLITE_PATH", str(tmp_path / "automatic.db"))
    first_started, release = Event(), Event()
    observed = []

    def respond(request, timeout):
        packet = json.loads(request.data)
        inputs = json.loads(packet["input"][0]["content"])
        observed.append(inputs)
        if not first_started.is_set():
            first_started.set()
            assert release.wait(timeout=10)
        if packet["text"]["format"]["name"] == "CandidateBatch":
            source = next(row for row in inputs["materials"]["sources"] if row["field"] == "keep")
            output = dict(candidates=[dict(
                label="根拠を整理する力", skillCode="TEST", confidence=80,
                growthAction="観点を次の共有会で試す", evidence=[dict(
                    materialId=source["id"], quote=source["text"])],
            )], notes="観測に基づく候補")
        else:
            source = inputs["sources"][0]
            output = dict(themeKey=FALLBACK_THEME_KEY, title="観点を説明する練習", body="理由を2つ添える",
                          aim="根拠を伝える", rationale="講師指摘を練習する", estimateMinutes=15,
                          messageForMember="小さく試しましょう", evidence=[dict(
                              materialId=source["id"], quote=source["text"])])
        return response_packet(output)

    monkeypatch.setattr(llm, "urlopen", respond)
    with TestClient(app) as member:
        admin, other = TestClient(app), TestClient(app)
        for client, name in ((member, "yuki"), (admin, "sensei"), (other, "sora")):
            assert client.post("/api/auth/login", json={
                "loginId": name, "password": f"caliboo-{name}"}).status_code == 200
        user_id = member.get("/api/auth/me").json()["id"]
        try:
            assert member.post("/api/report", json={
                "date": "2026-09-29", "keep": "理由を照合し境界値を整理した。",
                "problem": "伝え方が曖昧", "try": "共有会で試す", "status": "submitted",
            }).status_code == 200
            assert first_started.wait(timeout=5)
            assignment = admin.post("/api/assignments", json={
                "title": "観点の整理", "body": "境界値を示す", "targetUserId": user_id,
            }).json()
            assert member.post(f"/api/assignments/{assignment['id']}/submission", json={
                "answerText": "入力の下限と上限を分けて検証した。"}).status_code == 200
            assert admin.post(
                f"/api/assignments/{assignment['id']}/submissions/{user_id}/feedback", json={
                    "comment": "根拠の比較が丁寧。次は観点を説明しましょう。", "score": 85,
                }).status_code == 200
        finally:
            release.set()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            status = admin.get("/api/development/jobs").json()
            if not status["jobs"]:
                break
            time.sleep(0.05)
        assert status["jobs"] == []
        strengths = member.get("/api/development/strengths").json()
        assert strengths["candidates"] == [] and strengths["reviewPending"] is True
        final_input = next(inputs for inputs in reversed(observed) if "materials" in inputs)
        assert {"keep", "answer", "feedback"} <= {
            item["field"] for item in final_input["materials"]["sources"]}
        assert final_input["context"]["progress"]["reviewed"] == 2
        assert any("根拠の比較が丁寧" in item["text"]
                   for item in final_input["materials"]["sources"])
        response = admin.get(f"/api/development/strengths?userId={user_id}")
        candidate = response.json()["candidates"][0]
        assert admin.post(f"/api/development/strengths/{candidate['id']}/decision", json={
            "status": "approved", "label": candidate["label"],
            "growthAction": candidate["growthAction"],
        }).status_code == 200
        assert member.get("/api/home/summary").json()["strengths"][0]["label"] == candidate["label"]
        assert other.get("/api/development/strengths").json()["candidates"] == []
        action = member.post("/api/development/actions", json={
            "candidateId": candidate["id"], "title": "自分で選んだ共有会", "successCriteria": "改善点を試す",
        })
        assert action.status_code == 201
        proposals = admin.get("/api/assignment-proposals").json()["proposals"]
        assert len(proposals) == 1 and proposals[0]["target"]["id"] == user_id
        proposal_id = proposals[0]["id"]
        approved = admin.post(f"/api/assignment-proposals/{proposal_id}/approve", json={
            "title": "講師確認後の練習", "body": "理由を2つ添える", "messageForMember": "試しましょう",
        }).json()
        assert other.get(f"/api/assignments/{approved['assignmentId']}").status_code == 404
        assert member.get(f"/api/assignments/{approved['assignmentId']}").status_code == 200


def test_retry_auth_and_failure_history(client, admin_client, other_member_client, monkeypatch):
    user_id = client.get("/api/auth/me").json()["id"]
    job = admin_client.post(f"/api/development/strengths/{user_id}/request").json()

    def fail(instructions, materials, output_type, config):
        raise llm.LLMError("invalid_output")

    monkeypatch.setattr(llm, "generate_json", fail)
    config = llm.LLMSettings("test", "test")
    assert process_next(config)
    listing = admin_client.get("/api/development/jobs").json()["jobs"]
    assert listing[0]["status"] == "failed" and listing[0]["lastError"] == "invalid_output"
    assert client.get("/api/development/strengths").json()["jobs"][0]["status"] == "failed"
    path = f"/api/development/jobs/{job['id']}/retry"
    assert client.post(path).status_code == 403
    assert other_member_client.post(path).status_code == 403
    assert admin_client.post("/api/development/jobs/99999/retry").status_code == 404
    assert admin_client.post(path).status_code == 200
    assert admin_client.post(path).status_code == 409
    with session_scope() as session:
        assert session.get(AgentJobExecution, job["id"]).attempts == 0
        assert session.get(AgentJob, job["id"]).status == "pending"


def test_regeneration_checks_quotes_and_previous_version(client, admin_client, monkeypatch):
    user_id = client.get("/api/auth/me").json()["id"]
    proposal = admin_client.post("/api/assignment-proposals", json={"userId": user_id}).json()
    job = admin_client.post(f"/api/assignment-proposals/{proposal['id']}/regenerate",
                            json={"instruction": "短時間で実施できるように"}).json()

    def generate(instructions, materials, output_type, config):
        assert materials["instruction"] == "短時間で実施できるように"
        source = materials["sources"][0]
        return output_type(title="短時間の実践", body="観点を1つ記録する", messageForMember="試しましょう",
                           rationale="時間を絞って実施するため", estimateMinutes=10,
                           evidence=[dict(materialId=source["id"], quote=source["text"])])

    monkeypatch.setattr(llm, "generate_json", generate)
    config = llm.LLMSettings("test", "test")
    assert process_next(config)
    updated = admin_client.get(f"/api/assignment-proposals/{proposal['id']}").json()
    assert updated["title"] == "短時間の実践" and updated["generator"].startswith("openai:")
    assert admin_client.get(f"/api/development/jobs/{job['id']}").json()["status"] == "completed"
    assert len(admin_client.get(f"/api/assignment-proposals/{proposal['id']}/revisions").json()[
        "revisions"]) == 1
    stale = admin_client.post(f"/api/assignment-proposals/{proposal['id']}/regenerate",
                              json={"instruction": "短時間で実施できるように"}).json()
    admin_client.post(f"/api/assignment-proposals/{proposal['id']}/reject", json={})
    assert process_next(config)
    assert admin_client.get(f"/api/development/jobs/{stale['id']}").json()["status"] == "superseded"


@pytest.mark.parametrize("evidence", [
    [], [{"materialId": "material:999", "quote": "不明"}],
    [{"materialId": "material:0", "quote": "存在しない引用文"}],
])
def test_regeneration_rejects_unverified_evidence(client, admin_client, evidence):
    user_id = client.get("/api/auth/me").json()["id"]
    proposal = admin_client.post("/api/assignment-proposals", json={"userId": user_id}).json()
    job = admin_client.post(f"/api/assignment-proposals/{proposal['id']}/regenerate",
                            json={"instruction": "短時間に"}).json()
    result = admin_client.post(f"/api/assignment-proposals/agent-jobs/{job['id']}/result", json={
        "trace": {"provider": "openai", "model": "test", "promptVersion": "test"},
        "title": "変更された案", "body": "実践", "messageForMember": "試しましょう",
        "rationale": "練習するため", "estimateMinutes": 10, "evidence": evidence,
    })
    assert result.status_code == 422
    actual = admin_client.get(f"/api/assignment-proposals/{proposal['id']}").json()
    assert actual["title"] == proposal["title"] and actual["generator"] == proposal["generator"]
    assert admin_client.get(f"/api/development/jobs/{job['id']}").json()["status"] == "pending"
