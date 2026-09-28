"""本人の強みと講師のエージェント・評価ワークフロー。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from caliboo_api.auth.deps import get_current_user, require_admin
from caliboo_api.data.account_data import is_active, now_iso
from caliboo_api.data.agent_jobs import candidate_view, enqueue_strength, job_view
from caliboo_api.db import get_session
from caliboo_api.extension_models import (
    AgentJob, AgentJobContext, AgentJobExecution, StrengthCandidate, StrengthEvaluation,
)
from caliboo_api.models import User
from caliboo_api.schemas.agent_jobs import EvaluationInput, StrengthDecision, StrengthResult
from caliboo_api.schemas.strength_materials import StrengthAnalysisMaterials
from caliboo_api.services.strength_materials import normalize_strength_materials
from caliboo_api.services.llm import provider_name

router = APIRouter(prefix="/api/development", tags=["development"])


def validated_strength_materials(job: AgentJob) -> dict:
    try:
        return normalize_strength_materials(job.materials)
    except ValidationError:
        # !NOTE: 保存済み材料の不整合は入力結果を直しても解決しない。本文は漏らさない。
        raise HTTPException(409, "invalid or unsupported strength materials") from None


@router.get("/strength-materials/schema")
def strength_materials_schema(_admin: User = Depends(require_admin)) -> dict:
    return StrengthAnalysisMaterials.model_json_schema()


def member_or_404(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None or user.role != "member" or not is_active(session, user_id):
        raise HTTPException(404, "active member not found")
    return user


def pending_job(session: Session, job_id: int, kind: str) -> AgentJob:
    job = session.get(AgentJob, job_id)
    if job is None or job.kind != kind:
        raise HTTPException(404, "job not found")
    if job.status != "pending":
        raise HTTPException(409, "job is no longer pending")
    member_or_404(session, job.user_id)
    return job


@router.get("/strengths")
def list_strengths(
    userId: int | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    target = userId if userId is not None else user.id
    if user.role != "admin" and target != user.id:
        raise HTTPException(403, "forbidden")
    query = session.query(StrengthCandidate).filter_by(user_id=target)
    if user.role != "admin":
        query = query.filter_by(status="approved")
    jobs = (
        session.query(AgentJob)
        .filter_by(user_id=target, kind="strength")
        .order_by(AgentJob.id.desc())
        .limit(20)
        .all()
    )
    return {
        "candidates": [candidate_view(row) for row in query.order_by(StrengthCandidate.id.desc())],
        "jobs": [job_view(job, execution=session.get(AgentJobExecution, job.id)) for job in jobs],
        "reviewPending": session.query(StrengthCandidate).filter_by(
            user_id=target, status="pending").count() > 0,
    }


@router.post("/strengths/{user_id}/request")
def request_strength(
    user_id: int, _admin: User = Depends(require_admin), session: Session = Depends(get_session)
) -> dict:
    member_or_404(session, user_id)
    job = enqueue_strength(session, user_id)
    if job is None:
        raise HTTPException(409, "no submitted materials")
    return job_view(job)


@router.get("/jobs")
def list_jobs(
    _admin: User = Depends(require_admin), session: Session = Depends(get_session)
) -> dict:
    rows = session.query(AgentJob).filter(AgentJob.status.in_(["pending", "failed"])).order_by(
        AgentJob.id).all()
    return {"jobs": [job_view(row, execution=session.get(AgentJobExecution, row.id))
                     for row in rows], "provider": provider_name()}


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: int, _admin: User = Depends(require_admin),
              session: Session = Depends(get_session)) -> dict:
    job = session.get(AgentJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    member_or_404(session, job.user_id)
    updated = session.query(AgentJob).filter_by(id=job_id, status="failed").update(
        {"status": "pending"}, synchronize_session=False)
    if not updated:
        raise HTTPException(409, "only failed jobs can be retried")
    session.query(AgentJobExecution).filter_by(job_id=job_id).update(dict(
        attempts=0, lease_token=None, leased_until=0, next_attempt_at=0, last_error=None))
    session.commit()
    session.refresh(job)
    return job_view(job)


@router.get("/jobs/{job_id}")
def get_job(
    job_id: int, _admin: User = Depends(require_admin), session: Session = Depends(get_session)
) -> dict:
    job = session.get(AgentJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    result = job_view(job, True)
    if job.kind == "strength":
        result["materials"] = validated_strength_materials(job)
    context = session.get(AgentJobContext, job_id)
    if context is not None:
        result["context"] = context.context
    return result


@router.post("/jobs/{job_id}/strength-result")
def import_strength(
    job_id: int,
    payload: StrengthResult,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> dict:
    return complete_strength_result(job_id, payload, session)


def complete_strength_result(job_id: int, payload: StrengthResult, session: Session) -> dict:
    job = pending_job(session, job_id, "strength")
    sources = {item["id"]: item for item in validated_strength_materials(job)["sources"]}
    codes = [item.skillCode for item in payload.candidates]
    if len(codes) != len(set(codes)):
        raise HTTPException(422, "duplicate skill code")
    for candidate in payload.candidates:
        for evidence in candidate.evidence:
            source = sources.get(evidence.materialId)
            if (
                source is None
                or not source["evidenceEligible"]
                or evidence.quote not in source["text"]
            ):
                raise HTTPException(422, "evidence must quote an eligible source")
    updated = (
        session.query(AgentJob)
        .filter_by(id=job_id, status="pending")
        .update(
            {"status": "completed", "result": payload.model_dump(), "completed_at": now_iso()},
            synchronize_session=False,
        )
    )
    if not updated:
        raise HTTPException(409, "job is no longer pending")
    for candidate in payload.candidates:
        session.add(
            StrengthCandidate(
                user_id=job.user_id,
                job_id=job_id,
                label=candidate.label,
                skill_code=candidate.skillCode,
                confidence=candidate.confidence,
                evidence=[
                    dict(**evidence.model_dump(), source=sources[evidence.materialId])
                    for evidence in candidate.evidence
                ],
                growth_action=candidate.growthAction,
                status="pending",
            )
        )
    session.commit()
    return {"imported": len(payload.candidates)}


@router.post("/strengths/{candidate_id}/decision")
def decide_strength(
    candidate_id: int,
    payload: StrengthDecision,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> dict:
    row = session.get(StrengthCandidate, candidate_id)
    if row is None:
        raise HTTPException(404, "candidate not found")
    member_or_404(session, row.user_id)
    newer = (
        session.query(StrengthCandidate)
        .filter(
            StrengthCandidate.user_id == row.user_id,
            StrengthCandidate.skill_code == row.skill_code,
            StrengthCandidate.job_id > row.job_id,
            StrengthCandidate.status == "approved",
        )
        .first()
    )
    if newer is not None:
        raise HTTPException(409, "a newer candidate has already been approved")
    updated = (
        session.query(StrengthCandidate)
        .filter_by(id=candidate_id, status="pending")
        .update(
            {
                "status": payload.status,
                "label": payload.label,
                "growth_action": payload.growthAction,
                "decided_by": admin.id,
                "decided_at": now_iso(),
            },
            synchronize_session=False,
        )
    )
    if not updated:
        raise HTTPException(409, "candidate is no longer pending")
    if payload.status == "approved":
        session.query(StrengthCandidate).filter(
            StrengthCandidate.user_id == row.user_id,
            StrengthCandidate.skill_code == row.skill_code,
            StrengthCandidate.id != row.id,
            StrengthCandidate.status == "approved",
        ).update({"status": "superseded"}, synchronize_session=False)
    session.commit()
    session.refresh(row)
    return candidate_view(row)


@router.get("/evaluations/{job_id}/materials")
def evaluation_materials(
    job_id: int, _admin: User = Depends(require_admin), session: Session = Depends(get_session)
) -> dict:
    job = session.get(AgentJob, job_id)
    if job is None or job.kind != "strength":
        raise HTTPException(404, "strength job not found")
    # !NOTE: 人間ラベル付け用にはモデルの答えを含めない。
    return {"jobId": job.id, "materials": validated_strength_materials(job)}


@router.post("/evaluations/{job_id}")
def evaluate(
    job_id: int,
    payload: EvaluationInput,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
) -> dict:
    job = session.get(AgentJob, job_id)
    if job is None or job.kind != "strength" or job.status != "completed":
        raise HTTPException(404, "completed strength job not found")
    expected = set(payload.skillCodes)
    actual = {item["skillCode"] for item in job.result["candidates"]}
    match = "exact" if expected == actual else "partial" if expected & actual else "none"
    values = dict(
        job_id=job_id,
        reviewer_id=admin.id,
        match=match,
        accepted=payload.accepted,
        comment=payload.comment,
    )
    session.execute(
        insert(StrengthEvaluation)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["job_id", "reviewer_id"],
            set_=values,
        )
    )
    session.commit()
    return {"match": match}


@router.get("/evaluations")
def evaluation_summary(
    _admin: User = Depends(require_admin), session: Session = Depends(get_session)
) -> dict:
    grouped: dict[int, list[StrengthEvaluation]] = {}
    for row in session.query(StrengthEvaluation):
        grouped.setdefault(row.job_id, []).append(row)
    complete = [rows for rows in grouped.values() if len(rows) >= 2]
    observations = [row for rows in complete for row in rows]
    count = len(observations)
    agreement = sum(row.match != "none" for row in observations) / count if count else 0
    acceptance = sum(row.accepted for row in observations) / count if count else 0
    enough = len(complete) >= 20
    return dict(
        evaluatedJobs=len(complete),
        requiredJobs=20,
        requiredReviewers=2,
        agreement=agreement,
        acceptance=acceptance,
        threshold=0.8,
        status=(
            ("passed" if agreement >= 0.8 and acceptance >= 0.8 else "failed")
            if enough
            else "insufficient_data"
        ),
    )
