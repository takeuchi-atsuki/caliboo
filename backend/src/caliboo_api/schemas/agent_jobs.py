"""エージェント境界。サーバーは推論APIを呼ばず検証と保存を担う。"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]


class Evidence(BaseModel):
    materialId: str
    quote: Text


SkillCode = Literal["DBAD", "DTAN", "PROG", "DOCM", "TEST", "RLMT"]


class CandidateInput(BaseModel):
    label: Text
    skillCode: SkillCode
    confidence: int = Field(ge=0, le=100)
    evidence: list[Evidence] = Field(min_length=1, max_length=10)
    growthAction: Text


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
