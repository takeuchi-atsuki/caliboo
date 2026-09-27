"""資格勉強画面データのDBアクセス層。

!NOTE: `StudyProgress.certification`と`streakDays`は、ホーム画面(`home_profile`/
       `certifications`)と同一ユーザーの同一データであるため、既存の`home_profile`行を
       そのまま参照する(値を`study_data`側に複製しない)。
"""

from caliboo_api.db import session_scope
from caliboo_api.models import Certification, HomeProfile
from caliboo_api.extension_models import UserProgress
from caliboo_api.models import QuizQuestion as QuizQuestionModel
from caliboo_api.models import RelatedQuestion as RelatedQuestionModel
from caliboo_api.schemas.study import (
    ProgressCategory,
    QuizCategory,
    QuizQuestion,
    RelatedQuestionItem,
    StudyCertification,
    StudyProgress,
)


class _QuizRecord:
    def __init__(
        self,
        id: str,
        category: QuizCategory,
        text: str,
        choices: list[str],
        correct_index: int,
        explanation: str,
        time_limit_sec: int = 90,
        source: str | None = None,
    ) -> None:
        self.id = id
        self.category = category
        self.text = text
        self.choices = choices
        self.correct_index = correct_index
        self.explanation = explanation
        self.time_limit_sec = time_limit_sec
        self.source = source

    def to_public_question(self) -> QuizQuestion:
        return QuizQuestion(
            id=self.id,
            category=self.category,
            text=self.text,
            choices=self.choices,
            timeLimitSec=self.time_limit_sec,
            source=self.source,
        )


def _to_quiz_record(row: QuizQuestionModel) -> _QuizRecord:
    return _QuizRecord(
        id=row.id,
        category=row.category,
        text=row.text,
        choices=row.choices,
        correct_index=row.correct_index,
        explanation=row.explanation,
        time_limit_sec=row.time_limit_sec,
        source=row.source,
    )


def list_questions(category: QuizCategory | None) -> list[_QuizRecord]:
    with session_scope() as session:
        query = session.query(QuizQuestionModel).order_by(QuizQuestionModel.id)
        if category is not None:
            query = query.filter(QuizQuestionModel.category == category)
        return [_to_quiz_record(row) for row in query.all()]


def get_question(question_id: str) -> _QuizRecord | None:
    with session_scope() as session:
        row = session.get(QuizQuestionModel, question_id)
        if row is None:
            return None
        return _to_quiz_record(row)


def fetch_study_progress(user_id: int) -> StudyProgress:
    with session_scope() as session:
        profile = session.query(HomeProfile).filter(HomeProfile.user_id == user_id).first()
        certification = session.get(Certification, profile.certification_id)
        categories = session.query(UserProgress).filter_by(user_id=user_id).all()

        return StudyProgress(
            certification=StudyCertification(
                name=certification.name,
                achievementPercent=certification.achievement_percent,
            ),
            categories=[
                ProgressCategory(id=row.category_id, label=row.label, percent=row.percent)
                for row in categories
            ],
            streakDays=profile.user_streak_days,
        )


def fetch_related_questions() -> list[RelatedQuestionItem]:
    with session_scope() as session:
        rows = session.query(RelatedQuestionModel).all()
        return [
            RelatedQuestionItem(
                id=row.id,
                title=row.title,
                questionCount=row.question_count,
                tags=row.tags,
            )
            for row in rows
        ]
