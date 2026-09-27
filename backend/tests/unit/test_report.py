def test_submit_report_draft(client):
    payload = {
        "date": "2026-07-15",
        "keep": "テストを先に書けた",
        "problem": "レビュー待ちで手が止まった",
        "try": "並行タスクに着手する",
        "mood": ["fun", "tired"],
        "moodComment": "褒められて嬉しかった",
        "status": "draft",
    }

    response = client.post("/api/report", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["id"].startswith("rpt_20260715_")
    assert "savedAt" in body


def test_submit_report_submitted_without_mood(client):
    payload = {
        "date": "2026-07-16",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "submitted",
    }

    response = client.post("/api/report", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "submitted"


def test_submit_report_ids_are_unique(client):
    payload = {
        "date": "2026-07-17",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "draft",
    }

    first = client.post("/api/report", json=payload).json()
    second = client.post("/api/report", json=payload).json()

    assert first["id"] != second["id"]


def test_report_history_empty_when_no_reports(client):
    response = client.get("/api/report/history")

    assert response.status_code == 200
    assert response.json() == {"history": []}


def test_report_history_excludes_drafts(client):
    payload = {
        "date": "2026-07-18",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "draft",
    }

    client.post("/api/report", json=payload)
    response = client.get("/api/report/history")

    assert response.status_code == 200
    assert response.json() == {"history": []}


def test_report_history_returns_full_detail_for_submitted_reports(client):
    payload = {
        "date": "2026-07-19",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "mood": ["happy", "tired"],
        "moodComment": "moodComment",
        "status": "submitted",
    }

    client.post("/api/report", json=payload)
    response = client.get("/api/report/history")

    assert response.status_code == 200
    body = response.json()
    assert body["history"][0] == {
        "date": "2026-07-19",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "mood": ["happy", "tired"],
        "moodComment": "moodComment",
    }


def test_report_history_mood_empty_when_not_selected(client):
    payload = {
        "date": "2026-07-20",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "submitted",
    }

    client.post("/api/report", json=payload)
    response = client.get("/api/report/history")

    assert response.status_code == 200
    assert response.json()["history"][0]["mood"] == []


def test_report_history_sorted_by_date_descending(client):
    for date in ["2026-07-10", "2026-07-20", "2026-07-15"]:
        payload = {
            "date": date,
            "keep": "keep",
            "problem": "problem",
            "try": "try",
            "status": "submitted",
        }
        client.post("/api/report", json=payload)

    response = client.get("/api/report/history")

    assert response.status_code == 200
    dates = [item["date"] for item in response.json()["history"]]
    assert dates == ["2026-07-20", "2026-07-15", "2026-07-10"]


def test_report_drafts_empty_when_no_reports(client):
    response = client.get("/api/report/drafts")

    assert response.status_code == 200
    assert response.json() == {"drafts": []}


def test_report_drafts_excludes_submitted(client):
    payload = {
        "date": "2026-07-21",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "submitted",
    }

    client.post("/api/report", json=payload)
    response = client.get("/api/report/drafts")

    assert response.status_code == 200
    assert response.json() == {"drafts": []}


def test_report_drafts_returns_saved_draft_fields(client):
    payload = {
        "date": "2026-07-22",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "mood": ["happy"],
        "moodComment": "moodComment",
        "status": "draft",
    }

    created = client.post("/api/report", json=payload).json()
    response = client.get("/api/report/drafts")

    assert response.status_code == 200
    drafts = response.json()["drafts"]
    assert len(drafts) == 1
    assert drafts[0]["id"] == int(created["id"].rsplit("_", 1)[-1])
    assert drafts[0]["date"] == "2026-07-22"
    assert drafts[0]["keep"] == "keep"
    assert drafts[0]["problem"] == "problem"
    assert drafts[0]["try"] == "try"
    assert drafts[0]["mood"] == ["happy"]
    assert drafts[0]["moodComment"] == "moodComment"
    assert drafts[0]["savedAt"] == created["savedAt"]


def test_report_drafts_sorted_by_saved_at_descending(client):
    for date in ["2026-07-01", "2026-07-02", "2026-07-03"]:
        payload = {
            "date": date,
            "keep": "keep",
            "problem": "problem",
            "try": "try",
            "status": "draft",
        }
        client.post("/api/report", json=payload)

    response = client.get("/api/report/drafts")

    assert response.status_code == 200
    dates = [item["date"] for item in response.json()["drafts"]]
    assert dates == ["2026-07-03", "2026-07-02", "2026-07-01"]


def test_delete_report_draft_removes_it_from_list(client):
    payload = {
        "date": "2026-07-23",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "draft",
    }

    created = client.post("/api/report", json=payload).json()
    draft_id = int(created["id"].rsplit("_", 1)[-1])

    delete_response = client.delete(f"/api/report/drafts/{draft_id}")
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    list_response = client.get("/api/report/drafts")
    assert list_response.json() == {"drafts": []}


def test_delete_report_draft_missing_id_returns_404(client):
    response = client.delete("/api/report/drafts/999999")

    assert response.status_code == 404


def test_delete_report_draft_submitted_report_returns_404(client):
    payload = {
        "date": "2026-07-24",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "submitted",
    }

    created = client.post("/api/report", json=payload).json()
    report_id = int(created["id"].rsplit("_", 1)[-1])

    response = client.delete(f"/api/report/drafts/{report_id}")

    assert response.status_code == 404


def test_report_history_same_date_tiebreak_by_submission_order(client):
    first_payload = {
        "date": "2026-07-18",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "mood": ["happy"],
        "status": "submitted",
    }
    second_payload = {
        "date": "2026-07-18",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "mood": ["tired"],
        "status": "submitted",
    }

    client.post("/api/report", json=first_payload)
    client.post("/api/report", json=second_payload)
    response = client.get("/api/report/history")

    assert response.status_code == 200
    assert response.json()["history"][0]["mood"] == ["tired"]


def test_report_history_is_isolated_per_user(client, other_member_client):
    payload = {
        "date": "2026-08-01",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "submitted",
    }

    client.post("/api/report", json=payload)

    assert other_member_client.get("/api/report/history").json() == {"history": []}
    assert len(client.get("/api/report/history").json()["history"]) == 1


def test_report_drafts_are_isolated_per_user(client, other_member_client):
    payload = {
        "date": "2026-08-02",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "draft",
    }

    client.post("/api/report", json=payload)

    assert other_member_client.get("/api/report/drafts").json() == {"drafts": []}
    assert len(client.get("/api/report/drafts").json()["drafts"]) == 1


def test_delete_other_users_draft_returns_404(client, other_member_client):
    payload = {
        "date": "2026-08-03",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "draft",
    }
    created = client.post("/api/report", json=payload).json()
    draft_id = int(created["id"].rsplit("_", 1)[-1])

    response = other_member_client.delete(f"/api/report/drafts/{draft_id}")

    assert response.status_code == 404

    # 削除されずに残っていることも確認する
    assert len(client.get("/api/report/drafts").json()["drafts"]) == 1
