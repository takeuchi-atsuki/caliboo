from fastapi import APIRouter, HTTPException

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
def get_department_messages(dept_id: str) -> DepartmentMessagesResponse:
    messages = get_initial_messages(dept_id)
    if messages is None:
        raise HTTPException(status_code=404, detail=f"department not found: {dept_id}")
    return DepartmentMessagesResponse(deptId=dept_id, messages=messages)


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
def post_chat(payload: OjtChatRequest) -> ChatMessage:
    dept = get_department(payload.deptId)
    if dept is None:
        raise HTTPException(status_code=404, detail=f"department not found: {payload.deptId}")
    return build_ojt_reply(dept.name, payload.text)
