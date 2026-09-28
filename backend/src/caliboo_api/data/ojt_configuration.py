"""部署の設定と共通OJT処理の境界。会話履歴には変更を加えない。"""

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from caliboo_api.extension_models import OjtConfiguration
from caliboo_api.models import Department, DepartmentMessage, KnowledgeItem
from caliboo_api.schemas.ojt import (
    DEFAULT_QUICK_ASKS, KnowledgeContent, OjtConfigurationInput,
    OjtConfigurationUpdate, OjtConfigurationView, OjtDepartmentCreate,
)


def initialize_ojt_configurations(session: Session) -> None:
    for department in session.query(Department).all():
        if session.get(OjtConfiguration, department.id) is None:
            session.add(OjtConfiguration(
                department_id=department.id, quick_asks=list(DEFAULT_QUICK_ASKS),
                reply_guidance="", revision=1,
            ))


def configuration_view(session: Session, dept_id: str) -> OjtConfigurationView:
    department = session.get(Department, dept_id)
    if department is None:
        raise HTTPException(404, "department not found")
    config = session.get(OjtConfiguration, dept_id)
    messages = session.query(DepartmentMessage).filter_by(department_id=dept_id).order_by(
        DepartmentMessage.ordinal).all()
    knowledge = session.query(KnowledgeItem).filter_by(department_id=dept_id).order_by(
        KnowledgeItem.id).all()
    return OjtConfigurationView(
        id=dept_id, name=department.name, icon=department.icon, color=department.color,
        welcomeMessage="\n\n".join(message.text for message in messages),
        quickAsks=config.quick_asks, replyGuidance=config.reply_guidance,
        knowledge=[KnowledgeContent(title=item.title, description=item.description)
                   for item in knowledge], revision=config.revision,
    )


def _replace_content(session: Session, department: Department,
                     payload: OjtConfigurationInput) -> None:
    department.name, department.icon, department.color = payload.name, payload.icon, payload.color
    department.knowledge_count = len(payload.knowledge)
    session.query(DepartmentMessage).filter_by(department_id=department.id).delete()
    session.query(KnowledgeItem).filter_by(department_id=department.id).delete()
    session.add(DepartmentMessage(
        department_id=department.id, ordinal=1, role="bot", text=payload.welcomeMessage,
    ))
    session.add_all([
        KnowledgeItem(department_id=department.id, title=item.title, description=item.description)
        for item in payload.knowledge
    ])


def create_department(session: Session, payload: OjtDepartmentCreate) -> OjtConfigurationView:
    department = Department(id=payload.id, name=payload.name, icon=payload.icon,
                            color=payload.color, knowledge_count=0)
    session.add(department)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "department id already exists")
    session.add(OjtConfiguration(
        department_id=payload.id, quick_asks=payload.quickAsks,
        reply_guidance=payload.replyGuidance, revision=1,
    ))
    _replace_content(session, department, payload)
    session.flush()
    result = configuration_view(session, payload.id)
    session.commit()
    return result


def update_configuration(session: Session, dept_id: str,
                         payload: OjtConfigurationUpdate) -> OjtConfigurationView:
    department = session.get(Department, dept_id)
    if department is None:
        raise HTTPException(404, "department not found")
    # !NOTE: 比較と加算を同じUPDATEで行う。先にPythonで比較するだけでは同時保存を防げない。
    changed = session.execute(update(OjtConfiguration).where(
        OjtConfiguration.department_id == dept_id,
        OjtConfiguration.revision == payload.revision,
    ).values(quick_asks=payload.quickAsks, reply_guidance=payload.replyGuidance,
             revision=OjtConfiguration.revision + 1))
    if changed.rowcount != 1:
        raise HTTPException(409, "configuration changed; reload before saving")
    _replace_content(session, department, payload)
    session.flush()
    result = configuration_view(session, dept_id)
    session.commit()
    return result
