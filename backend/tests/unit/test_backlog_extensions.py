"""docs/backlog-implementation.md のAPI契約。"""

import time

from caliboo_api.db import bootstrap_db, session_scope
from caliboo_api.extension_models import (
    AccountState,
    AgentJob,
    LoginAttempt,
    StrengthEvaluation,
    UserProgress,
)
from caliboo_api.models import User

TRACE = {"provider": "codex_agent", "model": "test-agent", "promptVersion": "test"}
REPORT = dict(
    date="2026-09-28",
    keep="ログを照合し原因を特定した。",
    problem="説明が苦手。",
    try_="図を使う。",
    mood=["happy"],
    moodComment="達成感",
    status="submitted",
)


def submit_report(client, keep=None):
    body = dict(REPORT)
    body["try"] = body.pop("try_")
    if keep:
        body["keep"] = keep
    response = client.post("/api/report", json=body)
    assert response.status_code == 200, response.text


def create_user(admin_client, login="new-member", role="member", **extra):
    response = admin_client.post(
        "/api/users",
        json=dict(
            loginId=login,
            displayName="新人",
            password="a-long-password",
            role=role,
            **extra,
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()


def strength_job(admin_client, client):
    submit_report(client)
    user_id = client.get("/api/auth/me").json()["id"]
    job = admin_client.post(f"/api/development/strengths/{user_id}/request").json()
    detail = admin_client.get(f"/api/development/jobs/{job['id']}").json()
    source = next(item for item in detail["materials"]["sources"] if item["field"] == "keep")
    result = dict(
        trace=TRACE,
        candidates=[
            dict(
                label="照合して原因を見つける",
                skillCode="TEST",
                confidence=75,
                evidence=[dict(materialId=source["id"], quote=source["text"])],
                growthAction="確認手順を共有する",
            )
        ],
        notes="観測された行動のみ",
    )
    return job, result


def test_user_lifecycle_and_department_history(admin_client, client, anonymous_client):
    departments = client.get("/api/ojt/departments").json()["departments"]
    dept_id = departments[0]["id"]
    user = create_user(admin_client, departmentId=dept_id)
    assert user["history"][0]["departmentId"] == dept_id
    assert len(admin_client.get(f"/api/users?departmentId={dept_id}").json()["users"]) == 1
    assert client.get("/api/users").status_code == 403
    assert (
        anonymous_client.post(
            "/api/auth/login", json=dict(loginId=user["loginId"], password="a-long-password")
        ).status_code
        == 200
    )
    assert anonymous_client.get("/api/home/summary").json()["user"]["streakDays"] == 0
    assert all(
        item["percent"] == 0
        for item in anonymous_client.get("/api/study/progress").json()["categories"]
    )
    body = dict(
        displayName="変更後",
        role="member",
        active=True,
        departmentId=None,
        password="another-long-password",
    )
    updated = admin_client.post(f"/api/users/{user['id']}", json=body)
    assert updated.status_code == 200
    assert len(updated.json()["history"]) == 2
    assert anonymous_client.get("/api/auth/me").status_code == 401
    assert (
        anonymous_client.post(
            "/api/auth/login", json=dict(loginId=user["loginId"], password="another-long-password")
        ).status_code
        == 200
    )
    body.pop("password")
    body["active"] = False
    assert admin_client.post(f"/api/users/{user['id']}", json=body).status_code == 200
    assert anonymous_client.get("/api/auth/me").status_code == 401
    assert (
        anonymous_client.post(
            "/api/auth/login", json=dict(loginId=user["loginId"], password="another-long-password")
        ).status_code
        == 401
    )
    body["active"] = True
    assert admin_client.post(f"/api/users/{user['id']}", json=body).status_code == 200
    assert (
        anonymous_client.post(
            "/api/auth/login", json=dict(loginId=user["loginId"], password="another-long-password")
        ).status_code
        == 200
    )


def test_user_validation(admin_client):
    user = create_user(admin_client)
    body = dict(loginId="new-member", displayName="新人", password="a-long-password")
    assert admin_client.post("/api/users", json=body).status_code == 409
    body["loginId"] = "different"
    body["departmentId"] = "missing"
    assert admin_client.post("/api/users", json=body).status_code == 422
    update = dict(displayName="変更", role="member", active=True)
    assert admin_client.post("/api/users/99999", json=update).status_code == 404
    me = admin_client.get("/api/auth/me").json()["id"]
    assert admin_client.post(f"/api/users/{me}", json=update).status_code == 409
    assert (
        admin_client.post(
            f"/api/users/{user['id']}", json={**update, "password": "short"}
        ).status_code
        == 422
    )
    assert (
        admin_client.post(f"/api/users/{user['id']}", json={**update, "role": "admin"}).status_code
        == 200
    )


def test_login_throttle_persisted_and_expiry(anonymous_client, monkeypatch):
    now = int(time.time())
    with session_scope() as session:
        session.add_all([LoginAttempt(source="testclient", attempted_at=now) for i in range(20)])
        session.commit()
    response = anonymous_client.post(
        "/api/auth/login",
        json=dict(loginId="yuki", password="caliboo-yuki"),
        headers={"X-Forwarded-For": "spoofed"},
    )
    assert response.status_code == 429
    assert 1 <= int(response.headers["Retry-After"]) <= 900
    monkeypatch.setattr("caliboo_api.routers.auth.time.time", lambda: now + 901)
    assert (
        anonymous_client.post(
            "/api/auth/login", json=dict(loginId="yuki", password="caliboo-yuki")
        ).status_code
        == 200
    )


def test_ojt_persistence_isolation_and_reply(client, other_member_client, admin_client):
    dept = client.get("/api/ojt/departments").json()["departments"][0]
    assert dept["icon"].startswith("ph ")
    path = f"/api/ojt/departments/{dept['id']}"
    assert client.post(path + "/escalate").status_code == 409
    assert client.post("/api/ojt/chat", json=dict(deptId=dept["id"], text="設計の質問です"))
    history = client.get(path + "/messages").json()
    assert any(item["text"] == "設計の質問です" for item in history["messages"])
    assert not any(
        item["text"] == "設計の質問です"
        for item in other_member_client.get(path + "/messages").json()["messages"]
    )
    assert admin_client.get("/api/ojt/escalations").json()["threads"] == []
    assert client.post(path + "/escalate").status_code == 200
    assert client.post(path + "/escalate").status_code == 200
    inbox = admin_client.get(f"/api/ojt/escalations?departmentId={dept['id']}").json()
    assert inbox["pendingCount"] == 1
    reply_path = f"/api/ojt/escalations/{inbox['threads'][0]['id']}/reply"
    assert client.post(reply_path, json=dict(text="回答")).status_code == 403
    assert admin_client.post(reply_path, json=dict(text="一緒に確認しましょう")).status_code == 200
    assert admin_client.post(reply_path, json=dict(text="重複")).status_code == 409
    assert client.get(path + "/messages").json()["escalated"] is False
    assert "講師" in client.get(path + "/messages").json()["messages"][-1]["text"]
    assert client.post(path + "/escalate").status_code == 200
    assert (
        admin_client.post("/api/ojt/escalations/99999/reply", json=dict(text="回答")).status_code
        == 404
    )
    assert client.post("/api/ojt/departments/missing/escalate").status_code == 404


def test_quiz_images_and_personal_progress(client, other_member_client):
    before = other_member_client.get("/api/study/progress").json()
    result = client.post("/api/quiz/answer", json=dict(questionId="q_image_001", selectedIndex=0))
    assert result.status_code == 200 and result.json()["correct"]
    assert client.post(
        "/api/quiz/answer", json=dict(questionId="q_image_001", selectedIndex=0)
    ).json()["correct"]
    assert other_member_client.get("/api/study/progress").json() == before
    assert client.get("/api/study/progress").json() != before
    assert client.get("/quiz-assets/wave-a.svg").status_code == 200
    assert client.get("/quiz-assets/missing.svg").status_code == 404
    assert (
        client.post(
            "/api/quiz/answer", json=dict(questionId="q_image_001", selectedIndex=8)
        ).status_code
        == 422
    )
    from caliboo_api.data.study_data import get_question

    question = get_question("q_image_001").to_public_question().model_dump()
    assert question["choices"][0]["alt"]
    assert "correctIndex" not in question


def test_strength_import_approval_and_evaluation(client, admin_client, other_member_client):
    job, result = strength_job(admin_client, client)
    path = f"/api/development/jobs/{job['id']}/strength-result"
    assert client.post(path, json=result).status_code == 403
    assert admin_client.post(path, json=result).status_code == 200
    assert admin_client.post(path, json=result).status_code == 409
    assert client.get("/api/home/summary").json()["strengths"] == []
    candidate = admin_client.get(f"/api/development/strengths?userId={job['userId']}").json()[
        "candidates"
    ][0]
    decision = dict(status="approved", label="確認力", growthAction="比較表を作る")
    decision_path = f"/api/development/strengths/{candidate['id']}/decision"
    assert admin_client.post(decision_path, json=decision).status_code == 200
    assert admin_client.post(decision_path, json=decision).status_code == 409
    assert client.get("/api/home/summary").json()["strengths"][0]["label"] == "確認力"
    assert other_member_client.get("/api/home/summary").json()["strengths"] == []
    assert client.get(f"/api/development/strengths?userId={job['userId'] + 1}").status_code == 403
    materials = admin_client.get(f"/api/development/evaluations/{job['id']}/materials").json()
    assert "result" not in materials
    evaluate_path = f"/api/development/evaluations/{job['id']}"
    assert (
        admin_client.post(
            evaluate_path, json=dict(skillCodes=["TEST"], accepted=True, comment="一致")
        ).json()["match"]
        == "exact"
    )
    assert (
        admin_client.post(
            evaluate_path, json=dict(skillCodes=["TEST", "PROG"], accepted=True, comment="部分一致")
        ).json()["match"]
        == "partial"
    )
    assert (
        admin_client.post(
            evaluate_path, json=dict(skillCodes=[], accepted=False, comment="不一致")
        ).json()["match"]
        == "none"
    )
    assert admin_client.get("/api/development/evaluations").json()["status"] == "insufficient_data"


def test_strength_bad_evidence_stale_jobs_and_empty_inputs(client, admin_client):
    assert admin_client.post("/api/development/strengths/99999/request").status_code == 404
    sora = next(
        user for user in admin_client.get("/api/users").json()["users"] if user["loginId"] == "sora"
    )
    assert admin_client.post(f"/api/development/strengths/{sora['id']}/request").status_code == 409
    job, result = strength_job(admin_client, client)
    path = f"/api/development/jobs/{job['id']}/strength-result"
    candidate = result["candidates"][0]
    evidence = candidate["evidence"][0]
    original = dict(evidence)
    for change in [dict(quote="原文に存在しない"), dict(materialId="report:999:keep")]:
        evidence.update(change)
        assert admin_client.post(path, json=result).status_code == 422
        evidence.update(original)
    candidate_copy = dict(candidate)
    result["candidates"].append(candidate_copy)
    assert admin_client.post(path, json=result).status_code == 422
    result["candidates"].pop()
    submit_report(client, "テストケースを追加して再現を確認した。")
    assert admin_client.post(path, json=result).status_code == 409
    assert admin_client.get("/api/development/jobs/99999").status_code == 404
    assert (
        admin_client.post("/api/development/jobs/99999/strength-result", json=result).status_code
        == 404
    )
    assert (
        admin_client.post(
            "/api/development/strengths/99999/decision",
            json=dict(status="rejected", label="なし", growthAction="確認"),
        ).status_code
        == 404
    )
    assert admin_client.get("/api/development/evaluations/99999/materials").status_code == 404
    assert (
        admin_client.post(
            "/api/development/evaluations/99999",
            json=dict(skillCodes=[], accepted=False, comment="なし"),
        ).status_code
        == 404
    )


def test_manual_recipient_score_and_proposal_regeneration(
    client, admin_client, other_member_client
):
    user_id = client.get("/api/auth/me").json()["id"]
    assignment = admin_client.post(
        "/api/assignments", json=dict(title="個人演習", body="テストを書く", targetUserId=user_id)
    ).json()
    assert assignment["target"]["id"] == user_id
    assert other_member_client.get(f"/api/assignments/{assignment['id']}").status_code == 404
    assert (
        admin_client.post(
            "/api/assignments", json=dict(title="不正", body="課題", targetUserId=99999)
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/assignments/{assignment['id']}/submission",
            json=dict(answerText="境界値のテストを作成した。"),
        ).status_code
        == 200
    )
    feedback_path = f"/api/assignments/{assignment['id']}/submissions/{user_id}/feedback"
    assert admin_client.post(feedback_path, json=dict(comment="良い", score=101)).status_code == 422
    assert (
        admin_client.post(feedback_path, json=dict(comment="良い", score=85)).json()["submission"][
            "score"
        ]
        == 85
    )
    assert (
        admin_client.post(feedback_path, json=dict(comment="更新", score=90)).json()["submission"][
            "score"
        ]
        == 90
    )
    assert client.get(f"/api/assignments/{assignment['id']}").json()["submission"]["score"] == 90
    proposal = admin_client.post("/api/assignment-proposals", json=dict(userId=user_id)).json()
    path = f"/api/assignment-proposals/{proposal['id']}"
    job = admin_client.post(
        path + "/regenerate", json=dict(instruction="15分でできる課題へ")
    ).json()
    assert (
        admin_client.post(path + "/regenerate", json=dict(instruction="15分でできる課題へ")).json()[
            "id"
        ]
        == job["id"]
    )
    result = dict(
        trace=TRACE,
        title="境界値を1つ確認",
        body="入力0を確認する。",
        rationale="講師の時間指定",
        estimateMinutes=15,
        messageForMember="小さく始めよう",
    )
    result_path = f"/api/assignment-proposals/agent-jobs/{job['id']}/result"
    assert admin_client.post(result_path, json=result).status_code == 200
    assert admin_client.post(result_path, json=result).status_code == 409
    assert admin_client.get(path).json()["generator"].startswith("codex_agent")
    assert (
        admin_client.get(path + "/revisions").json()["revisions"][0]["previous"]["title"]
        == proposal["title"]
    )
    next_job = admin_client.post(path + "/regenerate", json=dict(instruction="さらに短く")).json()
    assert (
        admin_client.post(path + "/approve", json=dict(title="配信", body="実行する")).status_code
        == 200
    )
    assert (
        admin_client.post(
            f"/api/assignment-proposals/agent-jobs/{next_job['id']}/result", json=result
        ).status_code
        == 409
    )
    assert admin_client.post(path + "/regenerate", json=dict(instruction="変更")).status_code == 409
    assert (
        admin_client.post(
            "/api/assignment-proposals/99999/regenerate", json=dict(instruction="変更")
        ).status_code
        == 404
    )
    assert admin_client.get("/api/assignment-proposals/99999/revisions").status_code == 404


def test_extension_bootstrap_keeps_progress(client):
    user_id = client.get("/api/auth/me").json()["id"]
    with session_scope() as session:
        row = session.get(UserProgress, (user_id, "technology"))
        row.percent = 17
        session.commit()
    bootstrap_db()
    assert (
        next(
            item
            for item in client.get("/api/study/progress").json()["categories"]
            if item["id"] == "technology"
        )["percent"]
        == 17
    )


def test_evaluation_thresholds(admin_client):
    with session_scope() as session:
        user = session.query(User).first()
        reviewers = session.query(User).limit(2).all()
        for i in range(20):
            job = AgentJob(
                user_id=user.id,
                kind="strength",
                fingerprint=f"eval-{i}",
                status="completed",
                materials={},
                created_at="2026-09-28",
            )
            session.add(job)
            session.flush()
            for reviewer in reviewers:
                session.add(
                    StrengthEvaluation(
                        job_id=job.id,
                        reviewer_id=reviewer.id,
                        match="exact",
                        accepted=True,
                        comment="評価",
                    )
                )
        session.commit()
    summary = admin_client.get("/api/development/evaluations").json()
    assert summary["status"] == "passed" and summary["evaluatedJobs"] == 20
    with session_scope() as session:
        session.query(StrengthEvaluation).update({"accepted": False})
        session.commit()
    assert admin_client.get("/api/development/evaluations").json()["status"] == "failed"


def test_inactive_session_state_even_with_token(client):
    user_id = client.get("/api/auth/me").json()["id"]
    with session_scope() as session:
        session.get(AccountState, user_id).active = False
        session.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_automatic_proposal_daily_limit(client, admin_client):
    from caliboo_api.data.proposal_extensions import auto_propose

    user_id = client.get("/api/auth/me").json()["id"]
    for index in range(3):
        assert (
            admin_client.post(
                "/api/assignments",
                json=dict(
                    title=f"未提出{index}",
                    body="練習",
                    targetUserId=user_id,
                ),
            ).status_code
            == 200
        )
    submit_report(client)
    proposals = admin_client.get("/api/assignment-proposals").json()["proposals"]
    target = next(row for row in proposals if row["target"]["id"] == user_id)
    assert (
        admin_client.post(f"/api/assignment-proposals/{target['id']}/reject", json={}).status_code
        == 200
    )
    submit_report(client, "再提出した行動")
    assert not any(
        row["target"]["id"] == user_id
        for row in admin_client.get("/api/assignment-proposals").json()["proposals"]
    )
    with session_scope() as session:
        session.get(AccountState, user_id).active = False
        session.commit()
        auto_propose(session, user_id)


def test_strength_candidate_replacement_and_negative_material(client, admin_client):
    job, result = strength_job(admin_client, client)
    source = admin_client.get(f"/api/development/jobs/{job['id']}").json()["materials"]["sources"]
    problem = next(row for row in source if row["field"] == "problem")
    original = result["candidates"][0]["evidence"]
    result["candidates"][0]["evidence"] = [dict(materialId=problem["id"], quote=problem["text"])]
    path = f"/api/development/jobs/{job['id']}/strength-result"
    assert admin_client.post(path, json=result).status_code == 422
    result["candidates"][0]["evidence"] = original
    assert admin_client.post(path, json=result).status_code == 200
    candidates_path = f"/api/development/strengths?userId={job['userId']}"
    first = admin_client.get(candidates_path).json()["candidates"][0]
    decision = dict(status="approved", label="確認力", growthAction="共有する")
    assert (
        admin_client.post(
            f"/api/development/strengths/{first['id']}/decision", json=decision
        ).status_code
        == 200
    )
    submit_report(client, "ログを照合し原因を特定した。もう一度確認した。")
    pending = admin_client.get("/api/development/jobs").json()["jobs"][0]
    assert (
        admin_client.post(
            f"/api/development/jobs/{pending['id']}/strength-result", json=result
        ).status_code
        == 200
    )
    second = admin_client.get(candidates_path).json()["candidates"][0]
    assert (
        admin_client.post(
            f"/api/development/strengths/{second['id']}/decision", json=decision
        ).status_code
        == 200
    )
    assert len(client.get("/api/home/summary").json()["strengths"]) == 1
    assert (
        admin_client.post(
            f"/api/development/strengths/{first['id']}/decision", json=decision
        ).status_code
        == 409
    )
    submit_report(client, "検証の手順を実施した。")
    pending = admin_client.get("/api/development/jobs").json()["jobs"][0]
    assert (
        admin_client.post(
            f"/api/development/jobs/{pending['id']}/strength-result",
            json={
                "trace": TRACE,
                "candidates": [],
                "notes": "材料不足",
            },
        ).status_code
        == 200
    )


def test_legacy_extension_migration(bootstrapped_db):
    from caliboo_api.data.account_data import account_view, initialize_extensions, is_active
    from caliboo_api.models import Department, QuizQuestion

    with session_scope() as session:
        user = session.query(User).first()
        session.query(AccountState).delete()
        session.query(UserProgress).delete()
        department = session.query(Department).first()
        department.icon = "ph-code"
        session.query(QuizQuestion).filter_by(id="q_image_001").delete()
        session.commit()
        assert is_active(session, user.id)
        assert account_view(session, user)["active"]
        initialize_extensions(session)
        assert department.icon == "ph ph-code"
        assert session.get(QuizQuestion, "q_image_001") is not None
        assert session.query(UserProgress).count() == 12
