"""PL-7: 復習予定、個人ごとの優先順位、互換・同時更新。"""

from concurrent.futures import ThreadPoolExecutor

import pytest

from caliboo_api.data import quiz_review as review
from caliboo_api.data.study_data import list_questions
from caliboo_api.db import bootstrap_db, session_scope
from caliboo_api.extension_models import QuizAttempt, QuizReview, QuizSuccess, UserProgress


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(review, "now_epoch", lambda: 1000)


def add_review(session, user_id, question, correct, due_at):
    session.add(QuizReview(user_id=user_id, question_id=question.id, attempts=1,
                           correct_streak=int(correct), last_correct=correct,
                           last_answered_at=100, due_at=due_at))
    session.flush()


def test_due_mistakes_then_due_successes_then_unseen_and_owner_boundary(user_ids, monkeypatch):
    questions = list_questions(None)[:3]
    first, second, third = questions
    with session_scope() as session:
        add_review(session, user_ids["yuki"], first, False, 900)
        add_review(session, user_ids["yuki"], second, True, 800)
        add_review(session, user_ids["sora"], third, False, 700)
        chosen, reason = review.choose_question(session, user_ids["yuki"], questions, None)
        assert chosen.id == first.id and reason == "mistake_review"
        chosen, reason = review.choose_question(session, user_ids["yuki"], questions, first.id)
        assert chosen.id == second.id and reason == "scheduled_review"
        chosen, reason = review.choose_question(session, user_ids["sora"], questions, None)
        assert chosen.id == third.id and reason == "mistake_review"
        monkeypatch.setattr(review, "now_epoch", lambda: 799)
        chosen, reason = review.choose_question(session, user_ids["yuki"], questions, None)
        assert chosen.id == third.id and reason == "new"


def test_oldest_due_and_future_schedule_and_single_question(user_ids, monkeypatch):
    questions = list_questions(None)[:2]
    with session_scope() as session:
        add_review(session, user_ids["yuki"], questions[0], False, 500)
        add_review(session, user_ids["yuki"], questions[1], False, 700)
        chosen, reason = review.choose_question(session, user_ids["yuki"], questions, None)
        assert chosen.id == questions[0].id and reason == "mistake_review"
        monkeypatch.setattr(review, "now_epoch", lambda: 400)
        chosen, reason = review.choose_question(session, user_ids["yuki"], questions, None)
        assert chosen.id == questions[0].id and reason == "practice"
        chosen, reason = review.choose_question(
            session, user_ids["yuki"], [questions[0]], questions[0].id)
        assert chosen.id == questions[0].id


def test_legacy_successes_are_not_new_and_migration_preserves_progress(user_ids):
    user_id = user_ids["yuki"]
    questions = list_questions(None)[:2]
    with session_scope() as session:
        session.add(QuizSuccess(user_id=user_id, question_id=questions[0].id))
        progress = session.query(UserProgress).filter_by(user_id=user_id).first()
        progress.percent = 73
        category = progress.category_id
        session.commit()
    bootstrap_db()
    with session_scope() as session:
        assert session.get(UserProgress, (user_id, category)).percent == 73
        assert session.query(QuizReview).count() == session.query(QuizAttempt).count() == 0
        chosen, reason = review.choose_question(session, user_id, questions, None)
        assert chosen.id == questions[1].id and reason == "new"
        chosen, reason = review.choose_question(session, user_id, questions, questions[1].id)
        assert chosen.id == questions[0].id and reason == "practice"


def test_spaced_intervals_cap_and_mistake_reset(user_ids):
    user_id = user_ids["yuki"]
    question_id = list_questions(None)[0].id
    with session_scope() as session:
        for attempt, days in enumerate([1, 3, 7, 14, 30, 30], start=1):
            review.record_attempt(session, user_id, question_id, 0, True)
            session.commit()
            row = session.get(QuizReview, (user_id, question_id))
            assert row.attempts == attempt and row.correct_streak == attempt
            assert row.due_at == 1000 + days * review.DAY
        review.record_attempt(session, user_id, question_id, 1, False)
        session.commit()
        row = session.get(QuizReview, (user_id, question_id))
        assert row.correct_streak == 0 and row.last_correct is False
        assert row.due_at == 1600
        review.record_attempt(session, user_id, question_id, 0, True)
        session.commit()
        assert session.get(QuizReview, (user_id, question_id)).due_at == 1000 + review.DAY
        assert session.query(QuizAttempt).count() == 8


def test_attempt_transaction_rolls_back_together(user_ids):
    with pytest.raises(RuntimeError):
        with session_scope() as session:
            review.record_attempt(session, user_ids["yuki"], list_questions(None)[0].id, 0, True)
            raise RuntimeError("failed transaction")
    with session_scope() as session:
        assert session.query(QuizAttempt).count() == session.query(QuizReview).count() == 0


def test_concurrent_attempts_do_not_lose_counters(user_ids):
    user_id, question_id = user_ids["yuki"], list_questions(None)[0].id

    def answer(index):
        with session_scope() as session:
            review.record_attempt(session, user_id, question_id, index, True)
            session.commit()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(answer, range(4)))
    with session_scope() as session:
        row = session.get(QuizReview, (user_id, question_id))
        assert row.attempts == row.correct_streak == 4
        assert row.due_at == 1000 + 14 * review.DAY
        assert session.query(QuizAttempt).count() == 4
