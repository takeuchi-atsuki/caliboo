"""独立ラベルを解析結果の登録前に固定する実日報評価。"""

import hashlib
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from caliboo_api.auth.deps import require_admin
from caliboo_api.data.account_data import now_iso
from caliboo_api.db import get_session
from caliboo_api.extension_models import (
    StrengthEvaluation, StrengthHoldoutCase as Case, StrengthHoldoutLabel as Label,
)
from caliboo_api.models import Report, User
from caliboo_api.schemas.agent_jobs import SkillCode, StrengthResult, Text
from caliboo_api.services.strength_materials import normalize_strength_materials
from caliboo_api.services.strength_result import validate_evidence

router = APIRouter(prefix="/api/development/holdout", tags=["development"])


class CaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reportId: int = Field(gt=0)
    realAndUnseen: Literal[True]

    @field_validator("realAndUnseen", mode="before")
    @classmethod
    def require_real_unseen(cls, value):
        if value is not True:
            raise ValueError("real and unseen confirmation required")
        return value


class LabelInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    skillCodes: list[SkillCode] = Field(max_length=6)
    comment: Text
    outputUnseen: Literal[True]

    @field_validator("outputUnseen", mode="before")
    @classmethod
    def require_unseen(cls, value):
        if value is not True:
            raise ValueError("unseen confirmation required")
        return value


class ResultInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    materialsDigest: str = Field(pattern=r"^[a-f0-9]{64}$")
    result: StrengthResult


class AcceptanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    accepted: bool
    comment: Text


def get_case(session: Session, case_id: int) -> Case:
    row = session.get(Case, case_id)
    if row is None:
        raise HTTPException(404, "holdout case not found")
    return row


def match_codes(expected: list[str], result: dict) -> str:
    actual = {item["skillCode"] for item in result["candidates"]}
    return "exact" if set(expected) == actual else "partial" if set(expected) & actual else "none"


def case_view(session: Session, row: Case, reviewer_id: int) -> dict:
    labels = session.query(Label).filter_by(case_id=row.id).all()
    own = next((label for label in labels if label.reviewer_id == reviewer_id), None)
    return dict(
        id=row.id, reportId=row.report_id, materials=row.materials, materialsDigest=row.digest,
        createdAt=row.created_at, createdBy=row.created_by, labelCount=len(labels),
        status=row.status, result=row.result, resultAt=row.result_at, resultBy=row.result_by,
        # !NOTE: 結果登録前は、別の評価者のラベル・理由を返さない。
        labels=[dict(reviewerId=label.reviewer_id, skillCodes=label.skill_codes,
                     comment=label.comment, labeledAt=label.labeled_at,
                     accepted=label.accepted, acceptanceComment=label.acceptance_comment,
                     acceptedAt=label.accepted_at,
                     match=match_codes(label.skill_codes, row.result) if row.result else None)
                for label in labels if row.result is not None or label is own],
        ownLabelSubmitted=own is not None,
    )


@router.post("/cases", status_code=201)
def create_case(payload: CaseInput, admin: User = Depends(require_admin),
                session: Session = Depends(get_session)) -> dict:
    report = session.get(Report, payload.reportId)
    if report is None or report.status != "submitted":
        raise HTTPException(404, "submitted report not found")
    sources = [dict(id=f"report:{report.id}:{field}", text=text, date=report.date,
                    kind="report", field=field, evidenceEligible=field == "keep")
               for field, text in (("keep", report.keep), ("problem", report.problem),
                                   ("try", report.try_), ("moodComment", report.mood_comment))
               if text.strip()]
    if not sources:
        raise HTTPException(409, "report has no materials")
    materials = normalize_strength_materials({"sources": sources})
    digest = hashlib.sha256(json.dumps(materials, ensure_ascii=False,
                                       sort_keys=True).encode()).hexdigest()
    inserted = session.execute(insert(Case).values(
        report_id=report.id, materials=materials, digest=digest,
        created_by=admin.id, created_at=now_iso(), status="labeling",
    ).on_conflict_do_nothing()).rowcount
    if not inserted:
        raise HTTPException(409, "report already registered")
    session.commit()
    return case_view(session, session.query(Case).filter_by(report_id=report.id).one(), admin.id)


@router.get("/cases")
def list_cases(_admin: User = Depends(require_admin),
               session: Session = Depends(get_session)) -> dict:
    return {"cases": [dict(id=row.id, reportId=row.report_id, status=row.status)
                      for row in session.query(Case).order_by(Case.id.desc())]}


@router.get("/cases/{case_id}")
def read_case(case_id: int, admin: User = Depends(require_admin),
              session: Session = Depends(get_session)) -> dict:
    return case_view(session, get_case(session, case_id), admin.id)


@router.post("/cases/{case_id}/labels")
def label_case(case_id: int, payload: LabelInput, admin: User = Depends(require_admin),
               session: Session = Depends(get_session)) -> dict:
    get_case(session, case_id)
    # !NOTE: SQLiteの書込ロックを先に取得し、同時ラベルや結果登録と順序を競合させない。
    locked = session.query(Case).filter_by(id=case_id, status="labeling").update(
        {"status": "labeling"}, synchronize_session=False)
    if not locked or session.query(Label).filter_by(case_id=case_id).count() >= 2:
        raise HTTPException(409, "labels are closed")
    if session.get(Label, (case_id, admin.id)) is not None:
        raise HTTPException(409, "label is already fixed")
    session.add(Label(case_id=case_id, reviewer_id=admin.id,
                      skill_codes=sorted(set(payload.skillCodes)), comment=payload.comment,
                      labeled_at=now_iso()))
    session.commit()
    return case_view(session, get_case(session, case_id), admin.id)


@router.post("/cases/{case_id}/result")
def import_result(case_id: int, payload: ResultInput, admin: User = Depends(require_admin),
                  session: Session = Depends(get_session)) -> dict:
    row = get_case(session, case_id)
    if payload.materialsDigest != row.digest:
        raise HTTPException(409, "materials digest mismatch")
    validate_evidence(payload.result, row.materials)
    locked = session.query(Case).filter_by(id=case_id, status="labeling").update(
        {"status": "labeling"}, synchronize_session=False)
    if not locked or session.query(Label).filter_by(case_id=case_id).count() != 2:
        raise HTTPException(409, "two fixed labels required before result")
    # !NOTE: 旧形式を再取得したとき、追加フィールドの既定値で提出原文を変えない。
    row.result = payload.result.model_dump(exclude_unset=True)
    row.result_at, row.result_by, row.status = now_iso(), admin.id, "result_ready"
    session.commit()
    return case_view(session, row, admin.id)


@router.post("/cases/{case_id}/acceptance")
def accept_result(case_id: int, payload: AcceptanceInput, admin: User = Depends(require_admin),
                  session: Session = Depends(get_session)) -> dict:
    row = get_case(session, case_id)
    if row.result is None:
        raise HTTPException(409, "result is not ready")
    updated = session.query(Label).filter_by(
        case_id=case_id, reviewer_id=admin.id, accepted=None).update(dict(
            accepted=payload.accepted, acceptance_comment=payload.comment, accepted_at=now_iso()),
            synchronize_session=False)
    if not updated:
        raise HTTPException(409, "own unaccepted label required")
    session.commit()
    return case_view(session, row, admin.id)


def summary(session: Session) -> dict:
    complete = []
    rows = session.query(Case).filter(Case.result.is_not(None)).order_by(Case.id.desc()).all()
    trace = rows[0].result["trace"] if rows else None
    for row in rows:
        if row.result["trace"] != trace:
            continue
        labels = session.query(Label).filter_by(case_id=row.id).all()
        if len(labels) == 2 and all(label.accepted is not None for label in labels):
            complete.append((row, labels))
    votes = [(match_codes(label.skill_codes, row.result), label.accepted)
             for row, labels in complete for label in labels]
    agreement = sum(match != "none" for match, accepted in votes) / len(votes) if votes else 0
    acceptance = sum(accepted for match, accepted in votes) / len(votes) if votes else 0
    return dict(evaluatedJobs=len(complete), requiredJobs=20, requiredReviewers=2,
                agreement=agreement, acceptance=acceptance, threshold=0.8,
                trace=trace, legacyEvaluations=session.query(StrengthEvaluation).count(),
                status=("insufficient_data" if len(complete) < 20 else
                        "passed" if agreement >= 0.8 and acceptance >= 0.8 else "failed"))
