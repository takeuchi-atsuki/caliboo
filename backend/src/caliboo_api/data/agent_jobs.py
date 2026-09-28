"""解析材料のスナップショットと冪等ジョブ作成。"""

import hashlib
import json

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from caliboo_api.data.account_data import now_iso
from caliboo_api.extension_models import AgentJob, StrengthCandidate
from caliboo_api.models import AssignmentSubmission, Report
from caliboo_api.services.strength_materials import normalize_strength_materials


def strength_materials(session: Session, user_id: int) -> list[dict]:
    materials = []
    reports = session.query(Report).filter_by(user_id=user_id, status="submitted").order_by(
        Report.date.desc(), Report.id.desc()).limit(20).all()
    for report in reports:
        for field, text in (("keep", report.keep), ("problem", report.problem),
                            ("try", report.try_), ("moodComment", report.mood_comment)):
            if text.strip():
                materials.append(dict(id=f"report:{report.id}:{field}", text=text,
                                      date=report.date, kind="report", field=field,
                                      evidenceEligible=field == "keep"))
    submissions = session.query(AssignmentSubmission).filter_by(user_id=user_id).order_by(
        AssignmentSubmission.id.desc()).limit(20).all()
    for submission in submissions:
        for field, text in (("answer", submission.answer_text),
                            ("feedback", submission.feedback_comment)):
            if text and text.strip():
                materials.append(dict(id=f"submission:{submission.id}:{field}", text=text,
                                      date=submission.submitted_at, kind="submission",
                                      field=field, evidenceEligible=True))
    return materials


def create_job(session: Session, user_id: int, kind: str, materials: dict) -> AgentJob:
    encoded = json.dumps([user_id, kind, materials], ensure_ascii=False, sort_keys=True)
    fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
    session.execute(insert(AgentJob).values(
        user_id=user_id, kind=kind, materials=materials, fingerprint=fingerprint,
        status="pending", created_at=now_iso(),
    ).on_conflict_do_nothing(index_elements=["fingerprint"]))
    return session.query(AgentJob).filter_by(fingerprint=fingerprint).one()


def enqueue_strength(session: Session, user_id: int) -> AgentJob | None:
    materials = strength_materials(session, user_id)
    if not materials:
        return None
    snapshot = normalize_strength_materials({"sources": materials})
    job = create_job(session, user_id, "strength", snapshot)
    # !NOTE: 古い材料で後から返ってきた解析が最新の結果を上書きしないようにする。
    session.query(AgentJob).filter(
        AgentJob.user_id == user_id, AgentJob.kind == "strength", AgentJob.id < job.id,
        AgentJob.status == "pending",
    ).update({"status": "superseded"}, synchronize_session=False)
    session.commit()
    return job


def candidate_view(row: StrengthCandidate) -> dict:
    return dict(id=row.id, userId=row.user_id, jobId=row.job_id, label=row.label,
                skillCode=row.skill_code, confidence=row.confidence, evidence=row.evidence,
                growthAction=row.growth_action, status=row.status,
                decidedAt=row.decided_at)


def job_view(row: AgentJob, include_materials: bool = False) -> dict:
    result = dict(id=row.id, userId=row.user_id, kind=row.kind, status=row.status,
                  createdAt=row.created_at, completedAt=row.completed_at)
    if include_materials:
        result.update(materials=row.materials, result=row.result)
    return result
