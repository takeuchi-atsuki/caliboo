"""講師指示による再生成。手動取込と自動ワーカーで共通の検証を使う。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from caliboo_api.auth.deps import require_admin
from caliboo_api.data.account_data import now_iso
from caliboo_api.data.agent_jobs import create_job, job_view
from caliboo_api.data.assignment_proposal_data import get_proposal_detail
from caliboo_api.db import get_session
from caliboo_api.extension_models import AgentJob, ProposalRevision
from caliboo_api.models import AssignmentProposal, User
from caliboo_api.routers.development import pending_job
from caliboo_api.schemas.agent_jobs import ProposalAgentResult, Text

router = APIRouter(prefix="/api/assignment-proposals", tags=["assignment_proposals"])


class RegenerateRequest(BaseModel):
    instruction: Text


@router.post("/{proposal_id}/regenerate")
def regenerate(proposal_id: int, payload: RegenerateRequest,
               _admin: User = Depends(require_admin),
               session: Session = Depends(get_session)) -> dict:
    row = session.get(AssignmentProposal, proposal_id)
    if row is None:
        raise HTTPException(404, "proposal not found")
    if row.assignment_id is not None or row.decided_at is not None:
        raise HTTPException(409, "proposal is no longer pending")
    previous = dict(title=row.title, body=row.body, messageForMember=row.message_for_member,
                    rationale=row.rationale, estimateMinutes=row.estimate_minutes,
                    generator=row.generator)
    job = create_job(session, row.target_user_id, "proposal", dict(
        proposalId=row.id, instruction=payload.instruction, previous=previous,
        sources=row.materials, progress=row.progress,
    ))
    existing = session.query(ProposalRevision).filter_by(job_id=job.id).first()
    if existing is None:
        session.add(ProposalRevision(proposal_id=row.id, job_id=job.id,
                                     instruction=payload.instruction, previous=previous,
                                     created_at=now_iso()))
    session.commit()
    return job_view(job)


@router.get("/{proposal_id}/revisions")
def revisions(proposal_id: int, _admin: User = Depends(require_admin),
              session: Session = Depends(get_session)) -> dict:
    if session.get(AssignmentProposal, proposal_id) is None:
        raise HTTPException(404, "proposal not found")
    return {"revisions": [dict(id=row.id, jobId=row.job_id, instruction=row.instruction,
                               previous=row.previous, createdAt=row.created_at)
                          for row in session.query(ProposalRevision).filter_by(
                              proposal_id=proposal_id).order_by(ProposalRevision.id.desc())]}


@router.post("/agent-jobs/{job_id}/result")
def import_proposal(job_id: int, payload: ProposalAgentResult,
                    _admin: User = Depends(require_admin),
                    session: Session = Depends(get_session)) -> dict:
    return complete_proposal_result(job_id, payload, session)


def complete_proposal_result(job_id: int, payload: ProposalAgentResult, session: Session) -> dict:
    job = pending_job(session, job_id, "proposal")
    if payload.trace.provider == "openai":
        sources = {f"material:{index}": item["quote"]
                   for index, item in enumerate(job.materials["sources"])}
        if not payload.evidence or any(
            evidence.materialId not in sources or
            evidence.quote not in sources[evidence.materialId] for evidence in payload.evidence
        ):
            raise HTTPException(422, "evidence must quote a proposal source")
    proposal_id = job.materials["proposalId"]
    previous = job.materials["previous"]
    # !NOTE: 配信済み/見送り済み、または別の再生成で変わった課題案へ上書きしない。
    updated = session.query(AssignmentProposal).filter(
        AssignmentProposal.id == proposal_id, AssignmentProposal.assignment_id.is_(None),
        AssignmentProposal.decided_at.is_(None), AssignmentProposal.title == previous["title"],
        AssignmentProposal.body == previous["body"],
        AssignmentProposal.generator == previous["generator"],
    ).update(dict(title=payload.title, body=payload.body,
                  message_for_member=payload.messageForMember or None,
                  rationale=payload.rationale, estimate_minutes=payload.estimateMinutes,
                  generator=f"{payload.trace.provider}:{payload.trace.model}:{job_id}"),
             synchronize_session=False)
    if not updated:
        raise HTTPException(409, "proposal changed; request a fresh regeneration")
    updated_job = session.query(AgentJob).filter_by(id=job.id, status="pending").update(
        dict(status="completed", result=payload.model_dump(), completed_at=now_iso()),
        synchronize_session=False,
    )
    if not updated_job:
        session.rollback()
        raise HTTPException(409, "job is no longer pending")
    session.commit()
    return get_proposal_detail(proposal_id).model_dump()
