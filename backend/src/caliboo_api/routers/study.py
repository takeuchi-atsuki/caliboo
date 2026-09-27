from fastapi import APIRouter, Depends

from caliboo_api.auth.deps import get_current_user
from caliboo_api.data.study_data import fetch_related_questions, fetch_study_progress
from caliboo_api.models import User
from caliboo_api.schemas.common import ChatMessage
from caliboo_api.schemas.study import RelatedQuestionsResponse, StudyChatRequest, StudyProgress
from caliboo_api.services.chat_reply import build_study_reply

router = APIRouter(prefix="/api/study", tags=["study"])


@router.get("/progress", response_model=StudyProgress)
def get_progress(user: User = Depends(get_current_user)) -> StudyProgress:
    return fetch_study_progress(user.id)


@router.get("/related-questions", response_model=RelatedQuestionsResponse)
def get_related_questions() -> RelatedQuestionsResponse:
    return RelatedQuestionsResponse(items=fetch_related_questions())


@router.post("/chat", response_model=ChatMessage)
def post_chat(payload: StudyChatRequest) -> ChatMessage:
    return build_study_reply(payload.text)
