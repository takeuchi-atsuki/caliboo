from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from caliboo_api.auth.deps import get_current_user, require_admin, require_member
from caliboo_api.data.account_data import now_iso
from caliboo_api.data.ojt_history import (
    append_message, escalation_view, messages_for, thread_for,
)
from caliboo_api.db import get_session
from caliboo_api.extension_models import OjtThread
from caliboo_api.models import User

from caliboo_api.data.ojt_data import (
    fetch_departments,
    get_department,
    get_initial_messages,
    get_knowledge,
)
from caliboo_api.schemas.common import ChatMessage
from caliboo_api.schemas.ojt import (
    DepartmentKnowledgeResponse,
    DepartmentMessagesResponse,
    DepartmentsResponse,
    OjtChatRequest,
)
from caliboo_api.services.chat_reply import build_ojt_reply

router = APIRouter(prefix="/api/ojt", tags=["ojt"])


@router.get("/departments", response_model=DepartmentsResponse)
def list_departments() -> DepartmentsResponse:
    return DepartmentsResponse(departments=fetch_departments())


@router.get(
    "/departments/{dept_id}/messages",
    response_model=DepartmentMessagesResponse,
)
def get_department_messages(
    dept_id: str, user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DepartmentMessagesResponse:
    messages = get_initial_messages(dept_id)
    if messages is None:
        raise HTTPException(status_code=404, detail=f"department not found: {dept_id}")
    thread = thread_for(session, user.id, dept_id)
    history = messages_for(session, thread)
    session.commit()
    return DepartmentMessagesResponse(
        deptId=dept_id, messages=messages + history,
        escalated=thread.escalated_at is not None and thread.resolved_at is None,
    )


@router.get(
    "/departments/{dept_id}/knowledge",
    response_model=DepartmentKnowledgeResponse,
)
def get_department_knowledge(dept_id: str) -> DepartmentKnowledgeResponse:
    items = get_knowledge(dept_id)
    if items is None:
        raise HTTPException(status_code=404, detail=f"department not found: {dept_id}")
    return DepartmentKnowledgeResponse(deptId=dept_id, items=items)


@router.post("/chat", response_model=ChatMessage)
def post_chat(payload: OjtChatRequest, user: User = Depends(get_current_user),
              session: Session = Depends(get_session)) -> ChatMessage:
    dept = get_department(payload.deptId)
    if dept is None:
        raise HTTPException(status_code=404, detail=f"department not found: {payload.deptId}")
    thread = thread_for(session, user.id, payload.deptId)
    append_message(session, thread, "me", payload.text)
    reply = build_ojt_reply(dept.name, payload.text)
    saved = append_message(session, thread, "bot", reply.text,
                           [item.model_dump() for item in reply.references])
    session.commit()
    return saved


@router.post("/departments/{dept_id}/escalate")
def escalate(dept_id: str, user: User = Depends(require_member),
             session: Session = Depends(get_session)) -> dict:
    thread = thread_for(session, user.id, dept_id)
    if not messages_for(session, thread):
        raise HTTPException(409, "send a message before requesting help")
    if thread.escalated_at is None or thread.resolved_at is not None:
        thread.escalated_at = now_iso()
        thread.resolved_at = None
    session.commit()
    return {"escalated": True}


@router.get("/escalations")
def list_escalations(departmentId: str | None = None,
                     _admin: User = Depends(require_admin),
                     session: Session = Depends(get_session)) -> dict:
    query = session.query(OjtThread).filter(OjtThread.escalated_at.isnot(None))
    if departmentId:
        query = query.filter_by(department_id=departmentId)
    rows = query.order_by(OjtThread.escalated_at.desc()).all()
    return {"threads": [escalation_view(session, row) for row in rows],
            "pendingCount": sum(row.resolved_at is None for row in rows)}


class ReplyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000, pattern=r"\S")


@router.post("/escalations/{thread_id}/reply")
def reply_to_escalation(thread_id: int, payload: ReplyRequest,
                        admin: User = Depends(require_admin),
                        session: Session = Depends(get_session)) -> dict:
    thread = session.get(OjtThread, thread_id)
    if thread is None or thread.escalated_at is None:
        raise HTTPException(404, "escalation not found")
    if thread.resolved_at is not None:
        raise HTTPException(409, "already resolved")
    append_message(session, thread, "bot", f"{admin.display_name}（講師）: {payload.text}")
    thread.resolved_at = now_iso()
    session.commit()
    return escalation_view(session, thread)
