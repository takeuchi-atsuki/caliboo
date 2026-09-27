from pydantic import BaseModel

from caliboo_api.schemas.common import ChatMessage


class Department(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    knowledgeCount: int


class DepartmentsResponse(BaseModel):
    departments: list[Department]


class DepartmentMessagesResponse(BaseModel):
    deptId: str
    messages: list[ChatMessage]


class KnowledgeItem(BaseModel):
    id: str
    title: str
    description: str


class DepartmentKnowledgeResponse(BaseModel):
    deptId: str
    items: list[KnowledgeItem]


class OjtChatRequest(BaseModel):
    deptId: str
    text: str
