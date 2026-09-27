"""OJT画面データのDBアクセス層。"""

from caliboo_api.db import session_scope
from caliboo_api.models import Department as DepartmentModel
from caliboo_api.models import DepartmentMessage, KnowledgeItem as KnowledgeItemModel
from caliboo_api.schemas.common import ChatMessage
from caliboo_api.schemas.ojt import Department, KnowledgeItem


def fetch_departments() -> list[Department]:
    with session_scope() as session:
        rows = session.query(DepartmentModel).all()
        return [
            Department(
                id=row.id,
                name=row.name,
                icon=row.icon,
                color=row.color,
                knowledgeCount=row.knowledge_count,
            )
            for row in rows
        ]


def get_department(dept_id: str) -> Department | None:
    with session_scope() as session:
        row = session.get(DepartmentModel, dept_id)
        if row is None:
            return None
        return Department(
            id=row.id,
            name=row.name,
            icon=row.icon,
            color=row.color,
            knowledgeCount=row.knowledge_count,
        )


def get_initial_messages(dept_id: str) -> list[ChatMessage] | None:
    with session_scope() as session:
        if session.get(DepartmentModel, dept_id) is None:
            return None

        rows = (
            session.query(DepartmentMessage)
            .filter(DepartmentMessage.department_id == dept_id)
            .order_by(DepartmentMessage.ordinal)
            .all()
        )
        return [
            ChatMessage(id=f"{dept_id}-m{row.ordinal}", role=row.role, text=row.text)
            for row in rows
        ]


def get_knowledge(dept_id: str) -> list[KnowledgeItem] | None:
    with session_scope() as session:
        if session.get(DepartmentModel, dept_id) is None:
            return None

        rows = (
            session.query(KnowledgeItemModel)
            .filter(KnowledgeItemModel.department_id == dept_id)
            .order_by(KnowledgeItemModel.id)
            .all()
        )
        return [
            KnowledgeItem(id=f"k{index}", title=row.title, description=row.description)
            for index, row in enumerate(rows, start=1)
        ]
