from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from caliboo_api.auth.deps import get_current_user
from caliboo_api.db import get_session
from caliboo_api.extension_models import QuizSuccess, UserProgress
from caliboo_api.models import Certification, HomeProfile, QuizQuestion as QuestionModel, User

from caliboo_api.data.study_data import get_question, list_questions
from caliboo_api.data.quiz_review import choose_question, record_attempt
from caliboo_api.schemas.study import (
    QuizAnswerRequest,
    QuizAnswerResponse,
    QuizCategory,
    QuizQuestion,
)

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.get("/next", response_model=QuizQuestion)
def get_next_quiz(
    category: QuizCategory | None = None,
    exclude_id: str | None = Query(default=None, alias="excludeId"),
    user: User = Depends(get_current_user), session: Session = Depends(get_session),
) -> QuizQuestion:
    candidates = list_questions(category)
    if not candidates:
        raise HTTPException(status_code=404, detail=f"no question for category: {category}")
    selected, reason = choose_question(session, user.id, candidates, exclude_id)
    result = selected.to_public_question()
    result.practiceReason = reason
    return result


@router.post("/answer", response_model=QuizAnswerResponse)
def answer_quiz(payload: QuizAnswerRequest, user: User = Depends(get_current_user),
                session: Session = Depends(get_session)) -> QuizAnswerResponse:
    record = get_question(payload.questionId)
    if record is None:
        raise HTTPException(status_code=404, detail=f"question not found: {payload.questionId}")
    if payload.selectedIndex >= len(record.choices):
        raise HTTPException(422, "choice index out of range")
    correct_answer = payload.selectedIndex == record.correct_index
    record_attempt(session, user.id, record.id, payload.selectedIndex, correct_answer)
    if correct_answer:
        session.execute(insert(QuizSuccess).values(
            user_id=user.id, question_id=record.id,
        ).on_conflict_do_nothing())
    for category in session.query(UserProgress).filter_by(user_id=user.id):
        total = session.query(QuestionModel).filter_by(category=category.category_id).count()
        correct = session.query(QuizSuccess).join(
            QuestionModel, QuizSuccess.question_id == QuestionModel.id,
        ).filter(QuizSuccess.user_id == user.id,
                 QuestionModel.category == category.category_id).count()
        category.percent = round(correct * 100 / total) if total else 0
    profile = session.query(HomeProfile).filter_by(user_id=user.id).one()
    certification = session.get(Certification, profile.certification_id)
    total = session.query(QuestionModel).count()
    correct = session.query(QuizSuccess).filter_by(user_id=user.id).count()
    certification.achievement_percent = round(correct * 100 / total) if total else 0
    session.commit()
    return QuizAnswerResponse(
        correct=payload.selectedIndex == record.correct_index,
        correctIndex=record.correct_index,
        explanation=record.explanation,
    )
