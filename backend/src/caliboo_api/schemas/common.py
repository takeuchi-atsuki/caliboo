from typing import Literal

from pydantic import BaseModel


class ChatReference(BaseModel):
    label: str


class ChatMessage(BaseModel):
    id: str
    role: Literal["bot", "me"]
    text: str
    references: list[ChatReference] = []
