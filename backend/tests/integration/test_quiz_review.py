"""PL-7: 本人の誤答→別問題→期限後の復習と、採点・進捗の整合性。"""

from caliboo_api.data import quiz_review as review
from caliboo_api.data.study_data import get_question
from caliboo_api.db import bootstrap_db, session_scope
from caliboo_api.extension_models import QuizAttempt, QuizReview, QuizSuccess


def test_personal_mistake_review_and_nonduplicate_progress(
        client, other_member_client, monkeypatch):
    now = [1000]
    monkeypatch.setattr(review, "now_epoch", lambda: now[0])
    question = client.get("/api/quiz/next?category=management").json()
    assert question["practiceReason"] == "new"
    record = get_question(question["id"])
    wrong = (record.correct_index + 1) % len(record.choices)
    user_id = client.get("/api/auth/me").json()["id"]
    assert client.post("/api/quiz/answer", json=dict(
        questionId=record.id, selectedIndex=wrong)).json()["correct"] is False
    next_question = client.get(f"/api/quiz/next?category=management&excludeId={record.id}").json()
    assert next_question["id"] != record.id and next_question["category"] == "management"
    now[0] = 1600
    due = client.get("/api/quiz/next?category=management").json()
    assert due["id"] == record.id and due["practiceReason"] == "mistake_review"
    assert "correctIndex" not in due and "explanation" not in due
    assert other_member_client.get("/api/quiz/next?category=management").json()[
        "practiceReason"] == "new"
    correct = dict(questionId=record.id, selectedIndex=record.correct_index)
    assert client.post("/api/quiz/answer", json=correct).json()["correct"] is True
    first_progress = client.get("/api/study/progress").json()
    assert client.post("/api/quiz/answer", json=correct).status_code == 200
    assert client.get("/api/study/progress").json() == first_progress
    bootstrap_db()
    with session_scope() as session:
        scheduled = session.get(QuizReview, (user_id, record.id))
        assert scheduled.attempts == 3 and scheduled.correct_streak == 2
        assert scheduled.due_at == 1600 + 3 * review.DAY
        assert session.query(QuizSuccess).filter_by(user_id=user_id).count() == 1
        assert session.query(QuizAttempt).filter_by(user_id=user_id).count() == 3
    now[0] += 3 * review.DAY
    scheduled = client.get("/api/quiz/next?category=management").json()
    assert scheduled["id"] == record.id and scheduled["practiceReason"] == "scheduled_review"


def test_invalid_answers_leave_history_and_schedule_unchanged(client):
    question = client.get("/api/quiz/next").json()
    before = client.get("/api/study/progress").json()
    for payload, status in [
        (dict(questionId="missing", selectedIndex=0), 404),
        (dict(questionId=question["id"], selectedIndex=1000), 422),
        (dict(questionId=question["id"], selectedIndex=-1), 422),
    ]:
        assert client.post("/api/quiz/answer", json=payload).status_code == status
    with session_scope() as session:
        assert session.query(QuizAttempt).count() == session.query(QuizReview).count() == 0
    assert client.get("/api/study/progress").json() == before
