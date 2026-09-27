from caliboo_api.data.study_data import get_question


def test_get_next_quiz_without_category(client):
    response = client.get("/api/quiz/next")

    assert response.status_code == 200
    body = response.json()
    assert "correctIndex" not in body
    assert "explanation" not in body


def test_get_next_quiz_with_category(client):
    response = client.get("/api/quiz/next", params={"category": "management"})

    assert response.status_code == 200
    assert response.json()["category"] == "management"


def test_get_next_quiz_invalid_category(client):
    response = client.get("/api/quiz/next", params={"category": "unknown"})

    assert response.status_code == 422


def test_get_next_quiz_no_candidates_returns_404(client, monkeypatch):
    import caliboo_api.routers.quiz as quiz_router

    monkeypatch.setattr(quiz_router, "list_questions", lambda category: [])

    response = client.get("/api/quiz/next")

    assert response.status_code == 404


def test_get_next_quiz_excludes_given_id(client):
    ids_seen = set()
    for _ in range(30):
        response = client.get(
            "/api/quiz/next", params={"category": "management", "excludeId": "q_201"}
        )
        ids_seen.add(response.json()["id"])

    assert "q_201" not in ids_seen


def test_get_next_quiz_falls_back_to_full_pool_when_exclude_leaves_no_candidate(
    client, monkeypatch
):
    import caliboo_api.routers.quiz as quiz_router
    from caliboo_api.schemas.study import QuizQuestion

    class _OnlyCandidate:
        id = "only"

        def to_public_question(self) -> QuizQuestion:
            return QuizQuestion(
                id="only", category="technology", text="t", choices=["a"], timeLimitSec=90
            )

    monkeypatch.setattr(quiz_router, "list_questions", lambda category: [_OnlyCandidate()])

    response = client.get("/api/quiz/next", params={"excludeId": "only"})

    assert response.status_code == 200
    assert response.json()["id"] == "only"


def test_answer_quiz_correct(client):
    question = client.get("/api/quiz/next").json()
    record = get_question(question["id"])

    response = client.post(
        "/api/quiz/answer",
        json={"questionId": question["id"], "selectedIndex": record.correct_index},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["correctIndex"] == record.correct_index
    assert body["explanation"]


def test_answer_quiz_wrong(client):
    question = client.get("/api/quiz/next").json()
    record = get_question(question["id"])
    wrong_index = (record.correct_index + 1) % len(question["choices"])

    response = client.post(
        "/api/quiz/answer",
        json={"questionId": question["id"], "selectedIndex": wrong_index},
    )

    assert response.status_code == 200
    assert response.json()["correct"] is False


def test_answer_quiz_not_found(client):
    response = client.post(
        "/api/quiz/answer",
        json={"questionId": "unknown", "selectedIndex": 0},
    )

    assert response.status_code == 404
