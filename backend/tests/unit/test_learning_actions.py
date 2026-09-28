"""PL-1/2: 自己決定した行動の保存・所有者・競合境界。"""

import pytest

from caliboo_api.db import bootstrap_db, session_scope
from caliboo_api.extension_models import AgentJob, StrengthCandidate

BODY = dict(title=" 観点を共有する ", successCriteria="2人から改善案をもらう", dueDate="2026-10-01")


def candidate_for(user_id, status="approved"):
    with session_scope() as session:
        job = AgentJob(user_id=user_id, kind="strength", fingerprint=f"{user_id}-{status}",
                       status="completed", materials={}, created_at="2026-09-29")
        session.add(job)
        session.flush()
        candidate = StrengthCandidate(user_id=user_id, job_id=job.id, label="確認力",
                                      skill_code="TEST", confidence=80, evidence=[],
                                      growth_action="観点を共有", status=status)
        session.add(candidate)
        session.commit()
        return candidate.id


def test_free_action_lifecycle_and_persistence(client):
    response = client.post("/api/development/actions", json=BODY)
    assert response.status_code == 201
    action = response.json()
    assert action["title"] == "観点を共有する"
    assert action["status"] == "planned"
    assert action["strengthSnapshot"] is None
    for state in ("in_progress", "completed", "planned", "cancelled"):
        response = client.post(f"/api/development/actions/{action['id']}", json={
            **action, "status": state, "reflection": "視点が増えた", "dueDate": None,
        })
        assert response.status_code == 200
        assert response.json()["revision"] == action["revision"] + 1
        action = response.json()
    bootstrap_db()
    assert client.get("/api/development/actions").json()["actions"] == [action]


def test_stale_update_cannot_overwrite_and_unknown_id_is_404(client):
    action = client.post("/api/development/actions", json=BODY).json()
    changed = {**action, "title": "変更後"}
    assert client.post(f"/api/development/actions/{action['id']}", json=changed).status_code == 200
    assert client.post(f"/api/development/actions/{action['id']}", json=action).status_code == 409
    assert client.post("/api/development/actions/9999", json=action).status_code == 404
    assert client.get("/api/development/actions").json()["actions"][0]["title"] == "変更後"


def test_owner_and_instructor_boundaries(client, admin_client, other_member_client):
    action = client.post("/api/development/actions", json=BODY).json()
    path = f"/api/development/actions?userId={action['userId']}"
    assert admin_client.get(path).json()["actions"] == [action]
    assert other_member_client.get(path).status_code == 403
    assert other_member_client.get("/api/development/actions").json()["actions"] == []
    assert other_member_client.post(
        f"/api/development/actions/{action['id']}", json=action).status_code == 404
    assert admin_client.post(
        f"/api/development/actions/{action['id']}", json=action).status_code == 403
    assert admin_client.post("/api/development/actions", json=BODY).status_code == 403
    assert admin_client.get("/api/development/actions?userId=99999").status_code == 404


def test_only_own_approved_strength_and_snapshot(client, other_member_client):
    user_id = client.get("/api/auth/me").json()["id"]
    candidate_id = candidate_for(user_id)
    response = client.post("/api/development/actions", json={**BODY, "candidateId": candidate_id})
    assert response.status_code == 201
    snapshot = response.json()["strengthSnapshot"]
    assert snapshot == dict(label="確認力", growthAction="観点を共有")
    assert other_member_client.post("/api/development/actions", json={
        **BODY, "candidateId": candidate_id}).status_code == 404
    with session_scope() as session:
        row = session.get(StrengthCandidate, candidate_id)
        row.label = "後の解析で変わった強み"
        row.status = "superseded"
        session.commit()
    saved = client.get("/api/development/actions").json()["actions"][0]
    assert saved["strengthSnapshot"] == snapshot
    assert client.post("/api/development/actions", json={
        **BODY, "candidateId": candidate_id}).status_code == 404
    pending_id = candidate_for(user_id, "pending")
    assert client.post("/api/development/actions", json={
        **BODY, "candidateId": pending_id}).status_code == 404


@pytest.mark.parametrize("change", [
    {"title": " "}, {"successCriteria": ""}, {"title": "x" * 1001},
    {"dueDate": "2026-02-30"}, {"candidateId": 0},
])
def test_invalid_create(client, change):
    assert client.post("/api/development/actions", json={**BODY, **change}).status_code == 422


def test_invalid_completion_and_revision(client):
    action = client.post("/api/development/actions", json=BODY).json()
    for change in ({"status": "completed", "reflection": " "}, {"status": "unknown"},
                   {"revision": 0}, {"reflection": "a" * 5001}):
        assert client.post(f"/api/development/actions/{action['id']}",
                           json={**action, **change}).status_code == 422
