from typing import Literal

from pydantic import BaseModel


class ChatReference(BaseModel):
    label: str
    knowledgeId: str | None = None
    quote: str | None = None


class ChatMessage(BaseModel):
    id: str
    role: Literal["bot", "me"]
    text: str
    references: list[ChatReference] = []
