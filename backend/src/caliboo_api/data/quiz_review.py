"""本人の誤答と復習時刻による出題。既存の正解済み件数は独立して維持する。"""

import random
import time

from sqlalchemy import case
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from caliboo_api.extension_models import QuizAttempt, QuizReview, QuizSuccess

DAY = 24 * 60 * 60
CORRECT_INTERVAL_DAYS = (1, 3, 7, 14, 30)
MISTAKE_INTERVAL_SECONDS = 10 * 60


def now_epoch() -> int:
    return int(time.time())


def record_attempt(session: Session, user_id: int, question_id: str,
                   selected_index: int, correct: bool) -> None:
    now = now_epoch()
    session.add(QuizAttempt(user_id=user_id, question_id=question_id,
                            selected_index=selected_index, correct=correct, answered_at=now))
    interval = DAY if correct else MISTAKE_INTERVAL_SECONDS
    # !NOTE: 既存行の回数をSQL内で更新し、同時解答でも回数や連続正解を取りこぼさない。
    intervals = [(QuizReview.correct_streak == index, days * DAY)
                 for index, days in enumerate(CORRECT_INTERVAL_DAYS[:-1])]
    next_interval = case(*intervals, else_=CORRECT_INTERVAL_DAYS[-1] * DAY)
    session.execute(insert(QuizReview).values(
        user_id=user_id, question_id=question_id, attempts=1,
        correct_streak=1 if correct else 0, last_correct=correct,
        last_answered_at=now, due_at=now + interval,
    ).on_conflict_do_update(index_elements=["user_id", "question_id"], set_={
        "attempts": QuizReview.attempts + 1,
        "correct_streak": QuizReview.correct_streak + 1 if correct else 0,
        "last_correct": correct, "last_answered_at": now,
        "due_at": now + next_interval if correct else now + MISTAKE_INTERVAL_SECONDS,
    }))


def choose_question(session: Session, user_id: int, candidates: list,
                    exclude_id: str | None) -> tuple:
    pool = [item for item in candidates if item.id != exclude_id] or candidates
    reviews = {row.question_id: row for row in session.query(QuizReview).filter_by(user_id=user_id)}
    successes = {row.question_id for row in session.query(QuizSuccess).filter_by(user_id=user_id)}
    now = now_epoch()

    def priority(question) -> tuple[int, int]:
        review = reviews.get(question.id)
        if review is not None and review.due_at <= now:
            return (1 if review.last_correct else 0), review.due_at
        if review is None and question.id not in successes:
            return 2, 0
        return 3, review.due_at if review is not None else 0

    best = min(priority(item) for item in pool)
    selected = random.choice([item for item in pool if priority(item) == best])
    reason = ("mistake_review", "scheduled_review", "new", "practice")[best[0]]
    return selected, reason
