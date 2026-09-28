"""PL-1〜3: 日報から講師承認、本人の行動と個人宛て課題へ。"""


def test_approved_strength_to_member_action_and_assignment(
    client, admin_client, other_member_client,
):
    user_id = client.get("/api/auth/me").json()["id"]
    assert client.post("/api/report", json={
        "date": "2026-09-29", "keep": "境界値を洗い出しテストした。",
        "problem": "説明が足りない", "try": "観点を共有する", "status": "submitted",
    }).status_code == 200
    job = next(job for job in admin_client.get("/api/development/jobs").json()["jobs"]
               if job["userId"] == user_id and job["kind"] == "strength")
    material = next(source for source in admin_client.get(
        f"/api/development/jobs/{job['id']}").json()["materials"]["sources"]
        if source["field"] == "keep")
    assert admin_client.post(f"/api/development/jobs/{job['id']}/strength-result", json={
        "trace": {"provider": "codex_agent", "model": "contract-test", "promptVersion": "test"},
        "candidates": [{"label": "確認力", "skillCode": "TEST", "confidence": 80,
                        "evidence": [{"materialId": material["id"], "quote": material["text"]}],
                        "growthAction": "レビューで観点を共有する"}], "notes": "API境界の検証",
    }).status_code == 200
    assert client.get("/api/development/strengths").json()["candidates"] == []
    candidates = admin_client.get(f"/api/development/strengths?userId={user_id}").json()
    candidate = candidates["candidates"][0]
    assert admin_client.post(f"/api/development/strengths/{candidate['id']}/decision", json={
        "status": "approved", "label": candidate["label"],
        "growthAction": candidate["growthAction"],
    }).status_code == 200
    assert client.get("/api/home/summary").json()["strengths"][0]["label"] == "確認力"
    action = client.post("/api/development/actions", json={
        "title": "自分で選んだ共有会", "successCriteria": "改善案を1つ試す",
        "candidateId": candidate["id"],
    }).json()
    assert action["strengthSnapshot"]["label"] == "確認力"
    assert action["title"] != candidate["growthAction"]
    assignment = admin_client.post("/api/assignments", json={
        "title": "共有会の準備", "body": "観点をまとめる", "targetUserId": user_id,
    }).json()
    own = client.get("/api/development/actions").json()
    assert any(item["id"] == assignment["id"] for item in own["assignments"])
    other = other_member_client.get("/api/development/actions").json()
    assert other["actions"] == []
    assert all(item["id"] != assignment["id"] for item in other["assignments"])
    assert client.post(f"/api/assignments/{assignment['id']}/submission",
                       json={"answerText": "境界値一覧を共有した"}).status_code == 200
    assert admin_client.post(f"/api/assignments/{assignment['id']}/submissions/{user_id}/feedback",
                             json={"comment": "理由も明確でした", "score": 90}).status_code == 200
    assert client.post(f"/api/development/actions/{action['id']}", json={
        **action, "status": "completed", "reflection": "質問から観点を追加できた",
    }).status_code == 200
    final = admin_client.get(f"/api/development/actions?userId={user_id}").json()
    assert final["actions"][0]["reflection"] == "質問から観点を追加できた"
    assert next(item for item in final["assignments"] if item["id"] == assignment["id"])[
        "status"] == "reviewed"
