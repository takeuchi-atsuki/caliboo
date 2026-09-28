"""アカウント管理と追加テーブルの冪等初期化。"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from caliboo_api.extension_models import AccountState, DepartmentHistory, UserProgress
from caliboo_api.models import (
    Certification,
    Department,
    HomeProfile,
    ProgressCategory,
    QuizQuestion,
    User,
)
from caliboo_api.data.seed import study_seed
from caliboo_api.data.ojt_configuration import initialize_ojt_configurations


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_active(session: Session, user_id: int) -> bool:
    state = session.get(AccountState, user_id)
    return state is None or state.active


def initialize_extensions(session: Session) -> None:
    initialize_ojt_configurations(session)
    for user in session.query(User).all():
        if session.get(AccountState, user.id) is None:
            session.add(AccountState(user_id=user.id, active=True))
        for category in session.query(ProgressCategory).all():
            if session.get(UserProgress, (user.id, category.id)) is None:
                session.add(
                    UserProgress(
                        user_id=user.id,
                        category_id=category.id,
                        label=category.label,
                        percent=category.percent,
                    )
                )
    for department in session.query(Department).all():
        if department.icon.startswith("ph-") and " " not in department.icon:
            department.icon = "ph " + department.icon
    for question in study_seed.QUIZ_QUESTIONS_SEED:
        if (
            isinstance(question["choices"][0], dict)
            and session.get(QuizQuestion, question["id"]) is None
        ):
            session.add(QuizQuestion(**question))
    session.commit()


def initialize_profile(session: Session, user_id: int) -> None:
    certification = Certification(name="基本情報技術者試験", achievement_percent=0)
    session.add(certification)
    session.flush()
    session.add(
        HomeProfile(
            user_id=user_id,
            user_streak_days=0,
            certification_id=certification.id,
            strength1_label="",
            strength1_tone="green",
            strength2_label="",
            strength2_tone="blue",
            strength3_label="",
            strength3_tone="purple",
        )
    )
    for category in session.query(ProgressCategory).all():
        session.add(
            UserProgress(
                user_id=user_id,
                category_id=category.id,
                label=category.label,
                percent=0,
            )
        )


def set_department(
    session: Session, user_id: int, department_id: str | None, admin_id: int
) -> None:
    if department_id and session.get(Department, department_id) is None:
        raise HTTPException(422, "department not found")
    state = session.get(AccountState, user_id)
    if state is None:
        state = AccountState(user_id=user_id, active=True)
        session.add(state)
    if state.department_id != department_id:
        state.department_id = department_id
        session.add(
            DepartmentHistory(
                user_id=user_id,
                department_id=department_id,
                changed_by=admin_id,
                changed_at=now_iso(),
            )
        )


def account_view(session: Session, user: User) -> dict:
    state = session.get(AccountState, user.id)
    history = (
        session.query(DepartmentHistory)
        .filter_by(user_id=user.id)
        .order_by(DepartmentHistory.id.desc())
        .all()
    )
    return dict(
        id=user.id,
        loginId=user.login_id,
        displayName=user.display_name,
        role=user.role,
        active=state.active if state else True,
        departmentId=state.department_id if state else None,
        history=[
            dict(departmentId=row.department_id, changedAt=row.changed_at, changedBy=row.changed_by)
            for row in history
        ],
    )
