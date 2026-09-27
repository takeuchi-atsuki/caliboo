from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from caliboo_api.auth.deps import get_current_user
from caliboo_api.data.report_data import (
    create_report,
    delete_draft,
    fetch_draft_list,
    fetch_report_history,
)
from caliboo_api.db import get_session
from caliboo_api.models import User
from caliboo_api.schemas.report import (
    ReportDraftListResponse,
    ReportHistoryResponse,
    ReportRequest,
    ReportResponse,
)

router = APIRouter(prefix="/api/report", tags=["report"])


@router.post("", response_model=ReportResponse)
def submit_report(
    payload: ReportRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ReportResponse:
    report = create_report(session, user.id, payload)
    report_id = f"rpt_{payload.date.replace('-', '')}_{report.id}"
    return ReportResponse(
        id=report_id,
        status=report.status,
        savedAt=report.saved_at,
    )


@router.get("/history", response_model=ReportHistoryResponse)
def get_report_history(user: User = Depends(get_current_user)) -> ReportHistoryResponse:
    return ReportHistoryResponse(history=fetch_report_history(user.id))


@router.get("/drafts", response_model=ReportDraftListResponse)
def get_report_drafts(user: User = Depends(get_current_user)) -> ReportDraftListResponse:
    return ReportDraftListResponse(drafts=fetch_draft_list(user.id))


@router.delete("/drafts/{report_id}", status_code=204)
def delete_report_draft(
    report_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    deleted = delete_draft(session, user.id, report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"draft not found: {report_id}")
    return Response(status_code=204)
