"""本人の行動サイクルと、本人向けに配信された学習内容。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from caliboo_api.auth.deps import get_current_user, require_member
from caliboo_api.data.account_data import now_iso
from caliboo_api.data.assignment_data import fetch_assignment_list
from caliboo_api.db import get_session
from caliboo_api.extension_models import LearningAction, StrengthCandidate
from caliboo_api.models import User
from caliboo_api.routers.development import member_or_404
from caliboo_api.schemas.learning_actions import ActionCreate, ActionUpdate

router = APIRouter(prefix="/api/development/actions", tags=["development"])


def action_view(row: LearningAction) -> dict:
    return dict(id=row.id, userId=row.user_id, candidateId=row.candidate_id,
                strengthSnapshot=row.strength_snapshot, title=row.title,
                successCriteria=row.success_criteria, dueDate=row.due_date,
                status=row.status, reflection=row.reflection, revision=row.revision,
                createdAt=row.created_at, updatedAt=row.updated_at)


@router.get("")
def list_actions(userId: int | None = None, user: User = Depends(get_current_user),
                 session: Session = Depends(get_session)) -> dict:
    target = userId if userId is not None else user.id
    if user.role != "admin" and target != user.id:
        raise HTTPException(403, "forbidden")
    member_or_404(session, target)
    rows = session.query(LearningAction).filter_by(user_id=target).order_by(
        LearningAction.id.desc()).all()
    return dict(actions=[action_view(row) for row in rows],
                assignments=fetch_assignment_list(target, "member"))


@router.post("", status_code=201)
def create_action(payload: ActionCreate, user: User = Depends(require_member),
                  session: Session = Depends(get_session)) -> dict:
    snapshot = None
    if payload.candidateId is not None:
        candidate = session.query(StrengthCandidate).filter_by(
            id=payload.candidateId, user_id=user.id, status="approved").first()
        if candidate is None:
            raise HTTPException(404, "approved strength not found")
        # !NOTE: 後続のAI解析で本人の決めた行動の意味を変えないため、選択時の表現を残す。
        snapshot = dict(label=candidate.label, growthAction=candidate.growth_action)
    row = LearningAction(user_id=user.id, candidate_id=payload.candidateId,
                         strength_snapshot=snapshot, title=payload.title,
                         success_criteria=payload.successCriteria,
                         due_date=payload.dueDate.isoformat() if payload.dueDate else None,
                         status="planned", reflection="", revision=1,
                         created_at=now_iso(), updated_at=now_iso())
    session.add(row)
    session.commit()
    session.refresh(row)
    return action_view(row)


@router.post("/{action_id}")
def update_action(action_id: int, payload: ActionUpdate, user: User = Depends(require_member),
                  session: Session = Depends(get_session)) -> dict:
    row = session.query(LearningAction).filter_by(id=action_id, user_id=user.id).first()
    if row is None:
        raise HTTPException(404, "action not found")
    updated = session.query(LearningAction).filter_by(
        id=action_id, user_id=user.id, revision=payload.revision).update(dict(
            title=payload.title, success_criteria=payload.successCriteria,
            due_date=payload.dueDate.isoformat() if payload.dueDate else None,
            status=payload.status, reflection=payload.reflection,
            revision=payload.revision + 1, updated_at=now_iso()), synchronize_session=False)
    if not updated:
        raise HTTPException(409, "action changed; reload before editing")
    session.commit()
    session.refresh(row)
    return action_view(row)
