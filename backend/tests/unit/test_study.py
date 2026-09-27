def test_get_progress(client):
    response = client.get("/api/study/progress")

    assert response.status_code == 200
    body = response.json()
    assert body["certification"]["name"] == "基本情報技術者"
    assert len(body["categories"]) == 3
    assert body["streakDays"] == 12


def test_get_progress_is_isolated_per_user(other_member_client):
    response = other_member_client.get("/api/study/progress")

    assert response.status_code == 200
    body = response.json()
    assert body["certification"]["achievementPercent"] == 20
    assert body["streakDays"] == 3


def test_get_related_questions(client):
    response = client.get("/api/study/related-questions")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 3


def test_post_study_chat(client):
    response = client.post("/api/study/chat", json={"text": "TCPとUDPの違いは？"})

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "bot"
    assert "TCPとUDPの違いは？" in body["text"]
