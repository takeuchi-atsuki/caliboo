"""AIの課題案(BACKLOG #17)のスキーマ。"""

from typing import Literal

from pydantic import BaseModel

from caliboo_api.schemas.assignment import NonEmptyText
from caliboo_api.schemas.report import Mood

ProposalStatus = Literal["pending", "approved", "rejected"]
MaterialKind = Literal["report", "feedback", "mood", "progress"]


class ProposalUserRef(BaseModel):
    """課題案APIで人を指す最小情報(対象者・決定者・生成対象一覧で共用)。"""

    id: int
    displayName: str


class ProposalMaterial(BaseModel):
    kind: MaterialKind
    date: str | None = None
    quote: str
    sourceLabel: str


class ProposalProgress(BaseModel):
    submittedCount: int
    reviewedCount: int
    notSubmittedCount: int
    recentMoods: list[Mood]


class ProposalListItem(BaseModel):
    id: int
    target: ProposalUserRef
    title: str
    aim: str
    status: ProposalStatus
    createdAt: str
    decidedAt: str | None = None


class ProposalMember(BaseModel):
    """課題案の生成対象を選ぶための新入社員一覧の1件。"""

    id: int
    displayName: str
    hasPending: bool


class ProposalListResponse(BaseModel):
    proposals: list[ProposalListItem]
    members: list[ProposalMember]
    pendingCount: int


class ProposalDetail(ProposalListItem):
    body: str
    messageForMember: str | None = None
    rationale: str
    estimateMinutes: int
    materials: list[ProposalMaterial]
    progress: ProposalProgress
    generator: str
    assignmentId: int | None = None
    rejectReason: str | None = None
    decidedBy: ProposalUserRef | None = None
    edited: bool


class ProposalCreateRequest(BaseModel):
    """講師による課題案生成リクエスト(対象の新入社員を指定する)。"""

    userId: int


class ProposalApproveRequest(BaseModel):
    """講師による配信リクエスト(生成時の内容を編集できる)。"""

    title: NonEmptyText
    body: NonEmptyText
    messageForMember: str = ""


class ProposalRejectRequest(BaseModel):
    """講師による見送りリクエスト(理由は任意)。"""

    reason: str | None = None
