"""エージェント境界。サーバーは推論APIを呼ばず検証と保存を担う。"""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
InterpretationText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10000)]
StrengthKind = Literal["ability", "work_style"]


class Evidence(BaseModel):
    materialId: str
    quote: Text


SkillCode = Literal["DBAD", "DTAN", "PROG", "DOCM", "TEST", "RLMT"]


class CandidateInput(BaseModel):
    label: Text
    skillCode: SkillCode
    kind: StrengthKind = "ability"
    summary: InterpretationText = ""
    scopeNote: InterpretationText = ""
    confidence: int = Field(ge=0, le=100)
    evidence: list[Evidence] = Field(min_length=1, max_length=10)
    growthAction: Text

    @model_validator(mode="after")
    def require_work_style_interpretation(self) -> Self:
        if self.kind == "work_style" and (not self.summary or not self.scopeNote):
            raise ValueError("work style requires summary and scope note")
        return self


class AgentTrace(BaseModel):
    provider: Literal["codex_agent", "openai"]
    model: Text
    promptVersion: Text


class StrengthResult(BaseModel):
    trace: AgentTrace
    candidates: list[CandidateInput] = Field(max_length=10)
    notes: Text


class StrengthDecision(BaseModel):
    status: Literal["approved", "rejected"]
    label: Text
    growthAction: Text
    kind: StrengthKind | None = None
    summary: InterpretationText | None = None
    scopeNote: InterpretationText | None = None


class EvaluationInput(BaseModel):
    skillCodes: list[SkillCode] = Field(max_length=20)
    accepted: bool
    comment: Text


class ProposalAgentResult(BaseModel):
    trace: AgentTrace
    title: Text
    body: Text
    messageForMember: str = ""
    rationale: Text
    estimateMinutes: int = Field(ge=5, le=480)
    evidence: list[Evidence] = Field(default_factory=list, max_length=10)
