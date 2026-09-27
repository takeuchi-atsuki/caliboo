from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

AssignmentStatus = Literal["not_submitted", "submitted", "reviewed"]

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AssignmentCreateRequest(BaseModel):
    """講師による課題作成リクエスト。"""

    title: NonEmptyText
    body: NonEmptyText
    targetUserId: int | None = None


class AssignmentSubmissionRequest(BaseModel):
    """新入社員による回答提出リクエスト。"""

    answerText: NonEmptyText


class AssignmentFeedbackRequest(BaseModel):
    """講師によるフィードバック入力リクエスト。"""

    comment: NonEmptyText
    score: int | None = Field(default=None, ge=0, le=100)


class AssignmentSubmissionDetail(BaseModel):
    answerText: str
    submittedAt: str
    feedbackComment: str | None = None
    feedbackAt: str | None = None
    score: int | None = None


class AssignmentTarget(BaseModel):
    """`target`(個人宛て課題の宛先)。全員宛ての課題は`None`になる。"""

    id: int
    displayName: str


class AssignmentListItem(BaseModel):
    id: int
    title: str
    status: AssignmentStatus
    createdAt: str
    target: AssignmentTarget | None = None


class AssignmentListResponse(BaseModel):
    assignments: list[AssignmentListItem]


class AssignmentDetail(BaseModel):
    id: int
    title: str
    body: str
    status: AssignmentStatus
    createdAt: str
    submission: AssignmentSubmissionDetail | None = None
    target: AssignmentTarget | None = None
    messageForMember: str | None = None


class MemberUser(BaseModel):
    """`MemberSubmission.user`(講師向け提出一覧に出す新入社員の最小情報)。"""

    id: int
    displayName: str


class MemberSubmission(BaseModel):
    """講師向け: 新入社員1人分の提出状況(`GET .../submissions`・フィードバック保存の要素)。"""

    user: MemberUser
    status: AssignmentStatus
    submission: AssignmentSubmissionDetail | None = None


class MemberSubmissionListResponse(BaseModel):
    submissions: list[MemberSubmission]
