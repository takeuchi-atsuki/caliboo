from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from caliboo_api.schemas.common import ChatMessage

DEFAULT_QUICK_ASKS = ["よく聞かれる質問は？", "参考資料はどこにある？", "初日にやることは？"]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class Department(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    knowledgeCount: int
    quickAsks: list[str] = Field(default_factory=lambda: list(DEFAULT_QUICK_ASKS))


class DepartmentsResponse(BaseModel):
    departments: list[Department]


class DepartmentMessagesResponse(BaseModel):
    deptId: str
    messages: list[ChatMessage]
    escalated: bool = False


class KnowledgeItem(BaseModel):
    id: str
    title: str
    description: str


class DepartmentKnowledgeResponse(BaseModel):
    deptId: str
    items: list[KnowledgeItem]


class OjtChatRequest(BaseModel):
    deptId: str
    text: str = Field(min_length=1, max_length=10000, pattern=r"\S")


class KnowledgeContent(BaseModel):
    title: str
    description: str


class KnowledgeInput(KnowledgeContent):
    model_config = ConfigDict(extra="forbid")
    title: ShortText
    description: LongText


class OjtConfigurationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    icon: Literal[
        "ph ph-code", "ph ph-shield-check", "ph ph-handshake",
        "ph ph-compass-tool", "ph ph-factory", "ph ph-briefcase",
    ]
    color: Literal["#d6ebff", "#cdeede", "#ffd9e6", "#e3ddff", "#ffe9c7", "#f4f0ec"]
    welcomeMessage: LongText
    quickAsks: list[ShortText] = Field(max_length=8)
    replyGuidance: str = Field(max_length=4000)
    knowledge: list[KnowledgeInput] = Field(max_length=100)


class OjtDepartmentCreate(OjtConfigurationInput):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{0,39}$")


class OjtConfigurationUpdate(OjtConfigurationInput):
    revision: int = Field(ge=1, strict=True)


class OjtConfigurationView(BaseModel):
    # !NOTE: 既存DBのアイコン・色を取得時には制限しない。保存時に選択肢へ揃える。
    id: str
    name: str
    icon: str
    color: str
    welcomeMessage: str
    quickAsks: list[str]
    replyGuidance: str
    knowledge: list[KnowledgeContent]
    revision: int
