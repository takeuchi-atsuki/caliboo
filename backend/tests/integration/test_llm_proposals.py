"""PL-4/5: 生成境界から引用検証・講師確認・個人配信まで。実ネットワークは禁止。"""

import json
from io import BytesIO

import pytest

from caliboo_api.db import session_scope
from caliboo_api.extension_models import AgentJobExecution, ProposalAutomation
from caliboo_api.models import AssignmentProposal
from caliboo_api.services import llm
from caliboo_api.services.ai_worker import process_next
from caliboo_api.services.assignment_proposal.theme_catalog import FALLBACK_THEME_KEY


@pytest.fixture()
def provider(monkeypatch):
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    monkeypatch.setenv("CALIBOO_AI_MODEL", "contract-test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-secret")

    proposal_inputs = []

    def respond(request, timeout):
        body = json.loads(request.data)
        inputs = json.loads(body["input"][0]["content"])
        if body["text"]["format"]["name"] == "CandidateBatch":
            return BytesIO(json.dumps(dict(status="completed", output=[dict(
                type="message", content=[dict(type="output_text", text=json.dumps(dict(
                    candidates=[], notes="材料から十分な強みは確定できない")))])])).encode())
        proposal_inputs.append(inputs)
        source = inputs["sources"][0]
        assert any(item["kind"] == "feedback" for item in inputs["sources"])
        assert "progress" in inputs
        output = dict(
            themeKey=FALLBACK_THEME_KEY, title="理由を添えて説明する", body="理由を2つ書く。",
            aim="説明を具体化する", rationale="日報とフィードバックを踏まえた練習。",
            messageForMember="小さな共有から始めましょう", estimateMinutes=15,
            evidence=[dict(materialId=source["id"], quote=source["text"])],
        )
        return BytesIO(json.dumps(dict(status="completed", output=[dict(type="message", content=[
            dict(type="output_text", text=json.dumps(output)),
        ])])).encode())

    monkeypatch.setattr(llm, "urlopen", respond)
    return proposal_inputs


def report(client):
    assert client.post("/api/report", json=dict(
        date="2026-09-29", keep="根拠を確認した", problem="説明が不足", try_="改善する",
        status="submitted",
    ) | {"try": "改善する"}).status_code == 200


def test_llm_proposal_requires_instructor_delivery(
    client, admin_client, other_member_client, provider,
):
    report(client)
    user_id = client.get("/api/auth/me").json()["id"]
    response = admin_client.post("/api/assignment-proposals", json={"userId": user_id})
    assert response.status_code == 201, response.text
    proposal = response.json()
    assert proposal["generator"].startswith("openai:contract-test-model:")
    assert proposal["status"] == "pending"
    assert proposal["materials"][0]["quote"] == "説明が不足"
    assert proposal["progress"]["recentReportCount"] == 1
    assert proposal["progress"]["recentMoods"] == []
    assert "test-only-secret" not in json.dumps(proposal)
    repeat = admin_client.post("/api/assignment-proposals", json={"userId": user_id})
    assert repeat.status_code == 200 and repeat.json()["id"] == proposal["id"]
    assert not any(row["title"] == proposal["title"] for row in client.get(
        "/api/assignments").json()["assignments"])
    approved = admin_client.post(f"/api/assignment-proposals/{proposal['id']}/approve", json={
        "title": "講師が調整した課題", "body": proposal["body"],
        "messageForMember": proposal["messageForMember"],
    }).json()
    assert client.get(f"/api/assignments/{approved['assignmentId']}").status_code == 200
    hidden = other_member_client.get(f"/api/assignments/{approved['assignmentId']}")
    assert hidden.status_code == 404


@pytest.mark.parametrize("report_count", [0, 1, 7])
def test_llm_recent_reports_snapshot(
    client, admin_client, other_member_client, provider, report_count,
):
    """合成AI応答による生成でも、使用した材料と保存済み進捗の日報範囲は同じ。"""
    user_id = client.get("/api/auth/me").json()["id"]

    def save_report(member, day, moods, status="submitted"):
        response = member.post("/api/report", json={
            "date": f"2026-10-{day:02d}", "keep": "", "problem": f"観測{day}。",
            "try": "", "mood": moods, "status": status,
        })
        assert response.status_code == 200

    save_report(client, 30, ["tired"], status="draft")
    save_report(other_member_client, 31, ["tired"])
    for day in range(1, report_count + 1):
        save_report(client, day, ["happy", "foggy"] if day % 2 == 0 else [])

    response = admin_client.post("/api/assignment-proposals", json={"userId": user_id})
    assert response.status_code == 201, response.text
    proposal = response.json()
    expected_days = list(range(report_count, max(report_count - 5, 0), -1))
    expected_moods = ["happy" for day in expected_days if day % 2 == 0]
    assert proposal["progress"]["recentReportCount"] == min(report_count, 5)
    assert proposal["progress"]["recentMoods"] == expected_moods
    assert proposal["progress"]["submittedCount"] == 2
    assert len(provider) == 1
    assert provider[0]["progress"] == proposal["progress"]
    assert [source["text"] for source in provider[0]["sources"] if source["kind"] == "report"] == [
        f"観測{day}。" for day in expected_days
    ]

    save_report(client, 20, ["fun"])
    detail = admin_client.get(f"/api/assignment-proposals/{proposal['id']}")
    assert detail.status_code == 200
    assert detail.json()["progress"] == proposal["progress"]
    with session_scope() as session:
        assert session.get(AssignmentProposal, proposal["id"]).progress == proposal["progress"]


def test_bad_output_does_not_save_and_can_retry(client, admin_client, provider, monkeypatch):
    report(client)
    user_id = client.get("/api/auth/me").json()["id"]
    valid = llm.urlopen
    monkeypatch.setattr(llm, "urlopen", lambda request, timeout: BytesIO(b'{"secret":"body"}'))
    response = admin_client.post("/api/assignment-proposals", json={"userId": user_id})
    assert response.status_code == 503 and "secret" not in response.text
    with session_scope() as session:
        assert session.query(AssignmentProposal).filter_by(target_user_id=user_id).count() == 0
    monkeypatch.setattr(llm, "urlopen", valid)
    retry = admin_client.post("/api/assignment-proposals", json={"userId": user_id})
    assert retry.status_code == 201


def test_automatic_failure_preserves_report_and_daily_retry(
    client, admin_client, provider, monkeypatch,
):
    user_id = client.get("/api/auth/me").json()["id"]
    for index in range(3):
        admin_client.post("/api/assignments", json={
            "title": f"課題{index}", "body": "課題文", "targetUserId": user_id,
        })
    valid = llm.urlopen

    def fail(request, timeout):
        raise TimeoutError()

    monkeypatch.setattr(llm, "urlopen", fail)
    report(client)
    config = llm.settings()
    assert process_next(config)  # 強み解析の1回目
    assert process_next(config)  # 初回課題案の1回目
    with session_scope() as session:
        assert session.get(ProposalAutomation, user_id).last_date == ""
        assert session.query(AssignmentProposal).filter_by(target_user_id=user_id).count() == 0
    monkeypatch.setattr(llm, "urlopen", valid)
    with session_scope() as session:
        session.query(AgentJobExecution).update({"next_attempt_at": 0})
        session.commit()
    assert process_next(config)
    assert process_next(config)
    with session_scope() as session:
        assert session.get(ProposalAutomation, user_id).last_date != ""
        proposal = session.query(AssignmentProposal).filter_by(target_user_id=user_id).one()
        assert proposal.progress["recentReportCount"] == 1
        assert proposal.progress["recentMoods"] == []
