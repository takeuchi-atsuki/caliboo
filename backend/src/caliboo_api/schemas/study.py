from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

QuizCategory = Literal["technology", "management", "strategy"]


class ProgressCategory(BaseModel):
    id: QuizCategory
    label: str
    percent: int


class StudyCertification(BaseModel):
    name: str
    achievementPercent: int


class StudyProgress(BaseModel):
    certification: StudyCertification
    categories: list[ProgressCategory]
    streakDays: int


class ImageChoice(BaseModel):
    text: str = ""
    imageUrl: str = Field(pattern=r"^/quiz-assets/[A-Za-z0-9_-]+\.svg$")
    alt: str = Field(min_length=1, max_length=500, pattern=r"\S")


class QuizQuestion(BaseModel):
    """フロントに渡す出題用データ。正解・解説は解答後まで含めない。"""

    id: str
    category: QuizCategory
    text: str
    choices: list[str | ImageChoice]
    timeLimitSec: int
    source: str | None = None
    practiceReason: Literal["mistake_review", "scheduled_review", "new", "practice"] = "practice"


class QuizAnswerRequest(BaseModel):
    questionId: str
    selectedIndex: int = Field(ge=0)


class QuizAnswerResponse(BaseModel):
    correct: bool
    correctIndex: int
    explanation: str


class RelatedQuestionItem(BaseModel):
    id: str
    title: str
    questionCount: int
    tags: list[str]


class RelatedQuestionsResponse(BaseModel):
    items: list[RelatedQuestionItem]


StudyChatText = Annotated[str, StringConstraints(min_length=1, max_length=10000, pattern=r"\S")]


class StudyChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["me", "bot"]
    text: StudyChatText


class StudyQuestionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: StudyChatText
    choices: list[Annotated[str, StringConstraints(min_length=1, max_length=2500)]] = Field(
        min_length=1, max_length=10)


class StudyChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: StudyChatText
    history: list[StudyChatTurn] = Field(default_factory=list, max_length=12)
    question: StudyQuestionContext | None = None
