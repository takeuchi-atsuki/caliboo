from fastapi import APIRouter, Depends, HTTPException, Query, Response

from caliboo_api.auth.deps import require_admin
from caliboo_api.data.assignment_proposal_data import (
    ProposalActionError,
    ProposalCreateError,
    approve_proposal,
    create_or_get_pending_proposal,
    get_proposal_detail,
    list_proposals,
    reject_proposal,
)
from caliboo_api.models import User
from caliboo_api.services.llm import LLMError
from caliboo_api.schemas.assignment_proposal import (
    ProposalApproveRequest,
    ProposalCreateRequest,
    ProposalDetail,
    ProposalListResponse,
    ProposalRejectRequest,
    ProposalStatus,
)

router = APIRouter(prefix="/api/assignment-proposals", tags=["assignment_proposals"])


@router.get("", response_model=ProposalListResponse)
def list_assignment_proposals(
    status: ProposalStatus | None = None,
    assignment_id: int | None = Query(default=None, alias="assignmentId"),
    _admin: User = Depends(require_admin),
) -> ProposalListResponse:
    proposals, members, pending_count = list_proposals(status, assignment_id)
    return ProposalListResponse(proposals=proposals, members=members, pendingCount=pending_count)


@router.post("", response_model=ProposalDetail, status_code=201)
def create_assignment_proposal(
    payload: ProposalCreateRequest,
    response: Response,
    _admin: User = Depends(require_admin),
) -> ProposalDetail:
    """課題案を生成する。対象の新入社員に確認待ちの課題案が既にあれば、
    新規作成せずそれを200で返す(冪等)。"""
    try:
        result = create_or_get_pending_proposal(payload.userId)
    except LLMError:
        raise HTTPException(503, "課題案を生成できませんでした。設定と材料を確認し再試行してください。") from None
    if result is ProposalCreateError.TARGET_NOT_FOUND:
        raise HTTPException(status_code=404, detail=f"member not found: {payload.userId}")

    detail, is_new = result
    if not is_new:
        response.status_code = 200
    return detail


@router.get("/{proposal_id}", response_model=ProposalDetail)
def get_assignment_proposal(
    proposal_id: int, _admin: User = Depends(require_admin)
) -> ProposalDetail:
    detail = get_proposal_detail(proposal_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"proposal not found: {proposal_id}")
    return detail


@router.post("/{proposal_id}/approve", response_model=ProposalDetail)
def approve_assignment_proposal(
    proposal_id: int,
    payload: ProposalApproveRequest,
    admin: User = Depends(require_admin),
) -> ProposalDetail:
    result = approve_proposal(
        proposal_id, payload.title, payload.body, payload.messageForMember, admin.id
    )
    if result is ProposalActionError.NOT_FOUND:
        raise HTTPException(status_code=404, detail=f"proposal not found: {proposal_id}")
    if result is ProposalActionError.NOT_PENDING:
        raise HTTPException(status_code=409, detail=f"proposal not pending: {proposal_id}")
    return result


@router.post("/{proposal_id}/reject", response_model=ProposalDetail)
def reject_assignment_proposal(
    proposal_id: int,
    payload: ProposalRejectRequest,
    admin: User = Depends(require_admin),
) -> ProposalDetail:
    result = reject_proposal(proposal_id, payload.reason, admin.id)
    if result is ProposalActionError.NOT_FOUND:
        raise HTTPException(status_code=404, detail=f"proposal not found: {proposal_id}")
    if result is ProposalActionError.NOT_PENDING:
        raise HTTPException(status_code=409, detail=f"proposal not pending: {proposal_id}")
    return result
