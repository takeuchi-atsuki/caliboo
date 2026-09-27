import random

from fastapi import APIRouter, HTTPException, Query

from caliboo_api.data.study_data import get_question, list_questions
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
) -> QuizQuestion:
    candidates = list_questions(category)
    if not candidates:
        raise HTTPException(status_code=404, detail=f"no question for category: {category}")
    pool = [candidate for candidate in candidates if candidate.id != exclude_id]
    if not pool:
        pool = candidates
    return random.choice(pool).to_public_question()


@router.post("/answer", response_model=QuizAnswerResponse)
def answer_quiz(payload: QuizAnswerRequest) -> QuizAnswerResponse:
    record = get_question(payload.questionId)
    if record is None:
        raise HTTPException(status_code=404, detail=f"question not found: {payload.questionId}")
    return QuizAnswerResponse(
        correct=payload.selectedIndex == record.correct_index,
        correctIndex=record.correct_index,
        explanation=record.explanation,
    )
