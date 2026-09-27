"""test-perspectives.md『未完了バックログ対応』の横断シナリオ。"""


def test_report_agent_review_home_flow(client, admin_client, other_member_client):
    user_id = client.get("/api/auth/me").json()["id"]
    assert (
        client.post(
            "/api/report",
            json={
                "date": "2026-09-28",
                "keep": "境界値のテストを追加した。",
                "problem": "説明が不足",
                "try": "共有する",
                "status": "submitted",
            },
        ).status_code
        == 200
    )
    jobs = admin_client.get("/api/development/jobs").json()["jobs"]
    job = next(row for row in jobs if row["userId"] == user_id and row["kind"] == "strength")
    packet = admin_client.get(f"/api/development/jobs/{job['id']}").json()
    material = next(row for row in packet["materials"]["sources"] if row["field"] == "keep")
    assert (
        admin_client.post(
            f"/api/development/jobs/{job['id']}/strength-result",
            json={
                "trace": {"provider": "codex_agent", "model": "test", "promptVersion": "test"},
                "candidates": [
                    {
                        "label": "境界値を確認する",
                        "skillCode": "TEST",
                        "confidence": 70,
                        "evidence": [{"materialId": material["id"], "quote": material["text"]}],
                        "growthAction": "観点を共有する",
                    }
                ],
                "notes": "API契約検証",
            },
        ).status_code
        == 200
    )
    assert client.get("/api/development/strengths").json()["candidates"] == []
    candidate = admin_client.get(f"/api/development/strengths?userId={user_id}").json()[
        "candidates"
    ][0]
    assert (
        admin_client.post(
            f"/api/development/strengths/{candidate['id']}/decision",
            json={
                "status": "approved",
                "label": "確認力",
                "growthAction": "チームへ共有",
            },
        ).status_code
        == 200
    )
    assert client.get("/api/home/summary").json()["strengths"][0]["label"] == "確認力"
    assert other_member_client.get("/api/home/summary").json()["strengths"] == []


def test_ojt_member_to_instructor_flow(client, admin_client, other_member_client):
    dept_id = client.get("/api/ojt/departments").json()["departments"][0]["id"]
    assert (
        client.post("/api/ojt/chat", json={"deptId": dept_id, "text": "相談したい"}).status_code
        == 200
    )
    assert client.post(f"/api/ojt/departments/{dept_id}/escalate").status_code == 200
    thread = admin_client.get("/api/ojt/escalations").json()["threads"][0]
    assert (
        admin_client.post(
            f"/api/ojt/escalations/{thread['id']}/reply",
            json={
                "text": "明日一緒に確認しましょう",
            },
        ).status_code
        == 200
    )
    path = f"/api/ojt/departments/{dept_id}/messages"
    assert "明日一緒に" in client.get(path).json()["messages"][-1]["text"]
    assert not any(
        "明日一緒に" in item["text"] for item in other_member_client.get(path).json()["messages"]
    )


def test_account_and_personal_assignment_flow(admin_client, anonymous_client, client):
    created = admin_client.post(
        "/api/users",
        json={
            "loginId": "joined",
            "displayName": "入社者",
            "password": "temporary-password",
        },
    )
    assert created.status_code == 201
    member_id = created.json()["id"]
    assert (
        anonymous_client.post(
            "/api/auth/login",
            json={
                "loginId": "joined",
                "password": "temporary-password",
            },
        ).status_code
        == 200
    )
    assert (
        anonymous_client.get("/api/study/progress").json()["certification"]["achievementPercent"]
        == 0
    )
    assignment = admin_client.post(
        "/api/assignments",
        json={
            "title": "個人の課題",
            "body": "手順を説明する",
            "targetUserId": member_id,
        },
    ).json()
    path = f"/api/assignments/{assignment['id']}"
    assert client.get(path).status_code == 404
    assert (
        anonymous_client.post(path + "/submission", json={"answerText": "確認した手順"}).status_code
        == 200
    )
    assert (
        admin_client.post(
            path + f"/submissions/{member_id}/feedback",
            json={
                "comment": "よく整理できた",
                "score": 80,
            },
        ).status_code
        == 200
    )
    assert anonymous_client.get(path).json()["submission"]["score"] == 80
    assert (
        admin_client.post(
            f"/api/users/{member_id}",
            json={
                "displayName": "入社者",
                "role": "member",
                "active": False,
            },
        ).status_code
        == 200
    )
    assert anonymous_client.get(path).status_code == 401
