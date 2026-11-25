"""外部provider専用の応答型。手動取込の旧形式互換とは分離する。"""

from pydantic import ConfigDict, Field

from caliboo_api.schemas.agent_jobs import (
    CandidateInput, Evidence, InterpretationText, StrengthKind,
)


class ProviderEvidence(Evidence):
    model_config = ConfigDict(extra="forbid")


class ProviderCandidate(CandidateInput):
    model_config = ConfigDict(extra="forbid")
    # !NOTE: manualの既定値を外し、送信するstrict schemaと検証側の必須項目を一致させる。
    kind: StrengthKind
    summary: InterpretationText
    scopeNote: InterpretationText
    evidence: list[ProviderEvidence] = Field(min_length=1, max_length=10)
