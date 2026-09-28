from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from caliboo_api.auth.deps import get_current_user, require_admin, require_member
from caliboo_api.data.assignment_data import (
    FeedbackSaveError,
    SubmissionSaveError,
    create_assignment,
    fetch_assignment_list,
    fetch_member_submissions,
    get_assignment_detail,
    save_member_feedback,
    save_submission,
)
from caliboo_api.db import get_session
from caliboo_api.data.agent_jobs import enqueue_strength
from caliboo_api.data.proposal_extensions import auto_propose
from caliboo_api.models import User
from caliboo_api.schemas.assignment import (
    AssignmentCreateRequest,
    AssignmentDetail,
    AssignmentFeedbackRequest,
    AssignmentListResponse,
    AssignmentSubmissionRequest,
    MemberSubmission,
    MemberSubmissionListResponse,
)

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


@router.get("", response_model=AssignmentListResponse)
def list_assignments(user: User = Depends(get_current_user)) -> AssignmentListResponse:
    return AssignmentListResponse(assignments=fetch_assignment_list(user.id, user.role))


@router.get("/{assignment_id}", response_model=AssignmentDetail)
def get_assignment(
    assignment_id: int, user: User = Depends(get_current_user)
) -> AssignmentDetail:
    detail = get_assignment_detail(assignment_id, user.id, user.role)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"assignment not found: {assignment_id}")
    return detail


@router.post("", response_model=AssignmentDetail)
def create_new_assignment(
    payload: AssignmentCreateRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> AssignmentDetail:
    return create_assignment(session, payload.title, payload.body, payload.targetUserId)


@router.post("/{assignment_id}/submission", response_model=AssignmentDetail)
def submit_assignment_answer(
    assignment_id: int,
    payload: AssignmentSubmissionRequest,
    session: Session = Depends(get_session),
    member: User = Depends(require_member),
) -> AssignmentDetail:
    result = save_submission(session, assignment_id, member.id, payload.answerText)
    if result is SubmissionSaveError.ASSIGNMENT_NOT_FOUND:
        raise HTTPException(status_code=404, detail=f"assignment not found: {assignment_id}")
    if result is SubmissionSaveError.ALREADY_REVIEWED:
        raise HTTPException(
            status_code=409, detail=f"assignment already reviewed: {assignment_id}"
        )
    enqueue_strength(session, member.id)
    auto_propose(session, member.id, "submission")
    return result


@router.get("/{assignment_id}/submissions", response_model=MemberSubmissionListResponse)
def list_member_submissions(
    assignment_id: int,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> MemberSubmissionListResponse:
    submissions = fetch_member_submissions(session, assignment_id)
    if submissions is None:
        raise HTTPException(status_code=404, detail=f"assignment not found: {assignment_id}")
    return MemberSubmissionListResponse(submissions=submissions)


@router.post("/{assignment_id}/submissions/{user_id}/feedback", response_model=MemberSubmission)
def submit_member_feedback(
    assignment_id: int,
    user_id: int,
    payload: AssignmentFeedbackRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> MemberSubmission:
    result = save_member_feedback(session, assignment_id, user_id, payload.comment, payload.score)
    if result is FeedbackSaveError.ASSIGNMENT_NOT_FOUND:
        raise HTTPException(status_code=404, detail=f"assignment not found: {assignment_id}")
    if result is FeedbackSaveError.USER_NOT_FOUND:
        raise HTTPException(status_code=404, detail=f"member not found: {user_id}")
    if result is FeedbackSaveError.NOT_SUBMITTED:
        raise HTTPException(status_code=409, detail=f"assignment not submitted: {assignment_id}")
    enqueue_strength(session, user_id)
    auto_propose(session, user_id, "feedback")
    return result
