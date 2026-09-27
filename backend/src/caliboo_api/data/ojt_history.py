"""本人×課の会話と明示相談。"""

from fastapi import HTTPException
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from caliboo_api.data.account_data import now_iso
from caliboo_api.extension_models import OjtMessage, OjtThread
from caliboo_api.models import Department, User
from caliboo_api.schemas.common import ChatMessage


def thread_for(session: Session, user_id: int, department_id: str) -> OjtThread:
    if session.get(Department, department_id) is None:
        raise HTTPException(404, "department not found")
    session.execute(insert(OjtThread).values(
        user_id=user_id, department_id=department_id,
    ).on_conflict_do_nothing(index_elements=["user_id", "department_id"]))
    return session.query(OjtThread).filter_by(
        user_id=user_id, department_id=department_id).one()


def append_message(session: Session, thread: OjtThread, role: str, text: str,
                   references: list | None = None) -> ChatMessage:
    row = OjtMessage(thread_id=thread.id, role=role, text=text,
                     references=references or [], created_at=now_iso())
    session.add(row)
    session.flush()
    return ChatMessage(id=f"ojt-{row.id}", role=role, text=text, references=row.references)


def messages_for(session: Session, thread: OjtThread) -> list[ChatMessage]:
    return [ChatMessage(id=f"ojt-{row.id}", role=row.role, text=row.text,
                        references=row.references) for row in session.query(OjtMessage).filter_by(
                            thread_id=thread.id).order_by(OjtMessage.id)]


def escalation_view(session: Session, thread: OjtThread) -> dict:
    user = session.get(User, thread.user_id)
    department = session.get(Department, thread.department_id)
    return dict(id=thread.id, userId=user.id, displayName=user.display_name,
                departmentId=department.id, departmentName=department.name,
                escalatedAt=thread.escalated_at, resolvedAt=thread.resolved_at,
                messages=[message.model_dump() for message in messages_for(session, thread)])
