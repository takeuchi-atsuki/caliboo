from typing import Literal

from pydantic import BaseModel, Field

Mood = Literal["happy", "fun", "foggy", "tired"]
ReportStatus = Literal["draft", "submitted"]


class ReportRequest(BaseModel):
    date: str
    keep: str
    problem: str
    try_: str = Field(alias="try")
    mood: list[Mood] = Field(default_factory=list)
    moodComment: str = ""
    status: ReportStatus

    model_config = {"populate_by_name": True}


class ReportResponse(BaseModel):
    id: str
    status: ReportStatus
    savedAt: str


class ReportHistoryItem(BaseModel):
    date: str
    keep: str
    problem: str
    try_: str = Field(alias="try")
    mood: list[Mood]
    moodComment: str = ""

    model_config = {"populate_by_name": True}


class ReportHistoryResponse(BaseModel):
    history: list[ReportHistoryItem]


class ReportDraftItem(BaseModel):
    id: int
    date: str
    savedAt: str
    keep: str
    problem: str
    try_: str = Field(alias="try")
    mood: list[Mood]
    moodComment: str = ""

    model_config = {"populate_by_name": True}


class ReportDraftListResponse(BaseModel):
    drafts: list[ReportDraftItem]
