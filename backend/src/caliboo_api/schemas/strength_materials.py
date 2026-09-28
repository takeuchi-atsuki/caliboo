"""実日報の強み解析へ渡す、原文と出典を保持した入力契約。"""

import re
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "strength-materials.v1"
SOURCE_ROLES = {
    "keep": "self_report",
    "problem": "difficulty",
    "try": "plan",
    "moodComment": "emotion",
    "answer": "work_product",
    "feedback": "mentor_feedback",
}


class _Source(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(pattern=r"^(report|submission):[1-9][0-9]*:[A-Za-z]+$")
    text: str = Field(min_length=1, description="引用用の原文。空白・改行も変更しない。")
    date: str = Field(description="保存済み日付/提出日時/講師コメント更新日時。書式変換せず保持する。")
    evidenceEligible: bool = Field(description="引用候補にできる項目か。達成の保証ではない。")

    @field_validator("text")
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source text must not be blank")
        return value

    @field_validator("evidenceEligible", mode="before")
    @classmethod
    def require_boolean(cls, value: bool) -> bool:
        # Literal[True/False]だけではPythonの1==True・0==Falseも受理される。
        if not isinstance(value, bool):
            raise ValueError("evidence eligibility must be a boolean")
        return value

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        if not re.fullmatch(rf"{self.kind}:[1-9][0-9]*:{self.field}", self.id):
            raise ValueError("source id must match its kind and field")
        return self


class KeepSource(_Source):
    kind: Literal["report"]
    field: Literal["keep"]
    evidenceEligible: Literal[True]
    sourceRole: Literal["self_report"] = Field(description="本人の申告。達成の事実性は別途判断。")


class ProblemSource(_Source):
    kind: Literal["report"]
    field: Literal["problem"]
    evidenceEligible: Literal[False]
    sourceRole: Literal["difficulty"] = Field(description="困りごと。達成の根拠にはしない。")


class TrySource(_Source):
    kind: Literal["report"]
    field: Literal["try"]
    evidenceEligible: Literal[False]
    sourceRole: Literal["plan"] = Field(description="今後の計画。実施済みと扱わない。")


class MoodCommentSource(_Source):
    kind: Literal["report"]
    field: Literal["moodComment"]
    evidenceEligible: Literal[False]
    sourceRole: Literal["emotion"] = Field(description="感情の文脈。技能の根拠にはしない。")


class AnswerSource(_Source):
    kind: Literal["submission"]
    field: Literal["answer"]
    evidenceEligible: Literal[True]
    sourceRole: Literal["work_product"] = Field(description="本人の提出物。指示の転記等は除く。")


class FeedbackSource(_Source):
    kind: Literal["submission"]
    field: Literal["feedback"]
    evidenceEligible: Literal[True]
    sourceRole: Literal["mentor_feedback"] = Field(description="講師の所見。単独で確定しない。")


StrengthSource = Annotated[
    KeepSource | ProblemSource | TrySource | MoodCommentSource | AnswerSource | FeedbackSource,
    Field(discriminator="field"),
]


class StrengthAnalysisMaterials(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schemaVersion: Literal["strength-materials.v1"]
    sources: list[StrengthSource] = Field(max_length=120)

    @field_validator("sources")
    @classmethod
    def require_unique_ids(cls, sources: list[StrengthSource]) -> list[StrengthSource]:
        ids = [source.id for source in sources]
        if len(ids) != len(set(ids)):
            raise ValueError("source ids must be unique")
        return sources
