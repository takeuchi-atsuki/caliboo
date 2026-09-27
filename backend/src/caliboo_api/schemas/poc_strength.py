"""強み解析PoCのスキーマ。

!NOTE: 本モジュールは他の`schemas/*.py`と異なり、フィールド名をcamelCaseで統一する
       (docs/api.md「強み解析PoC」節を参照)。仕様書§4のJSON例はsnake_caseで
       書かれているが、同ドキュメントは「PoC用の論理スキーマ(確定前提でなく叩き台)」
       と自ら述べており、表示契約として不変ではないため、本リポジトリの既存規約
       (camelCase)を優先する。仕様書のキー名との対応表はdocs/api.mdに置く。
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

StrengthStatus = Literal["confirmed", "tentative", "insufficient_evidence"]
OverallStatus = Literal["complete", "partial", "insufficient"]
LearningDelta = Literal["+", "0", "-"]
EvidenceKind = Literal["trajectory", "diary", "review"]
RunStatus = Literal["completed"]

# !NOTE: schemas/assignment.pyと同じ回避方法(空白のみの文字列を422で弾く)。
#        スキーマモジュールごとに定義する既存方針(共通utilを作らない)に合わせている。
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PocPersonaOption(BaseModel):
    personaKey: str
    label: str
    description: str


class PocPersonaListResponse(BaseModel):
    personas: list[PocPersonaOption]


class PocRunCreateRequest(BaseModel):
    personaKey: str


class PocTaskDefinition(BaseModel):
    taskId: NonEmptyText
    title: NonEmptyText
    description: NonEmptyText
    skillHint: str | None = None


class PocTrajectoryIteration(BaseModel):
    iteration: int
    task: PocTaskDefinition
    workerOutput: NonEmptyText
    trainerFeedback: NonEmptyText
    # 仕様書§2別案(Human-in-the-Loop)用。人間監督者が当該周のフィードバックを
    # 上書きした場合の内容。`mode: agent`(本案)では常にNone。
    humanOverride: str | None = None


class PocDiaryTask(BaseModel):
    time: NonEmptyText
    what: NonEmptyText
    progressDesc: NonEmptyText
    progressRate: int


class PocDiaryFeelings(BaseModel):
    emotion: NonEmptyText
    trigger: NonEmptyText
    nextAction: NonEmptyText


class PocDiaryKpt(BaseModel):
    keep: NonEmptyText
    problem: NonEmptyText
    try_: NonEmptyText = Field(alias="try")

    model_config = {"populate_by_name": True}


class PocDiary(BaseModel):
    date: str
    tasks: list[PocDiaryTask]
    feelings: PocDiaryFeelings
    kpt: PocDiaryKpt
    mentorComment: str


class PocReviewComment(BaseModel):
    agentKey: str
    reviewerRole: NonEmptyText
    magiTone: NonEmptyText
    comment: NonEmptyText
    flags: list[str]


class PocReviewsBundle(BaseModel):
    reviews: list[PocReviewComment]
    fanInComment: str
    fanInFlags: list[str]


class EvidenceSource(BaseModel):
    kind: EvidenceKind
    iteration: int | None = None
    field: str
    role: str | None = None


class StrengthEvidence(BaseModel):
    quote: str
    source: EvidenceSource


class LayerTask(BaseModel):
    framework: Literal["SFIA"] = "SFIA"
    skillCode: str
    skillName: str
    level: int


class LayerBehavior(BaseModel):
    framework: Literal["CliftonStrengths"] = "CliftonStrengths"
    themes: list[str]


class LayerWillSkill(BaseModel):
    quadrant: str
    policy: str


class LearningAgility(BaseModel):
    delta: LearningDelta
    note: str


class GrowthContent(BaseModel):
    title: str
    contentTag: str


class StrengthItem(BaseModel):
    id: str
    layerTask: LayerTask
    layerBehavior: LayerBehavior
    layerWillSkill: LayerWillSkill | None = None
    confidence: float
    status: StrengthStatus
    evidence: list[StrengthEvidence]
    learningAgility: LearningAgility
    growthContent: GrowthContent | None = None


class StrengthOutput(BaseModel):
    subjectId: str
    runId: str
    generatedAt: str
    provider: str
    strengths: list[StrengthItem]
    overallStatus: OverallStatus
    notes: str


class PocRunAgentTrace(BaseModel):
    """外部投入run(`POST /api/poc/runs/import`)で、どのエージェント定義が
    どのモデル・プロンプトバージョンで生成を担ったかの記録(仕様書§6トレーサビリティ)。
    """

    key: str
    model: str
    promptVersion: str


class PocRunTrace(BaseModel):
    """どの実装が出した結果かを後から追うための記録(仕様書§6のトレーサビリティ)。

    !NOTE: `scriptVersion`はペルソナ台本由来のrun(`POST /api/poc/runs`)でのみ設定される。
           外部投入run(`POST /api/poc/runs/import`)は台本を経由しないため常にNoneとなり、
           代わりに`agents`(生成を担ったエージェント定義)が設定される。
           `externalAnalysis`は、ルールベース解析(`strengths`)とは別モデルで解析エージェントが
           独立に出した結果(仕様書§2「評価者の分離」)。外部投入run側で解析結果の突き合わせを
           行った場合のみ設定される。
    """

    generationProvider: str
    analysisProvider: str
    scriptVersion: str | None = None
    agents: list[PocRunAgentTrace] | None = None
    externalAnalysis: StrengthOutput | None = None


class PocRunSummary(BaseModel):
    id: str
    personaKey: str
    subjectId: str
    label: str
    injectedPersona: str | None = None
    status: RunStatus
    createdAt: str


class PocRunListResponse(BaseModel):
    runs: list[PocRunSummary]


class PocRunDetail(BaseModel):
    id: str
    personaKey: str
    subjectId: str
    label: str
    injectedPersona: str | None = None
    status: RunStatus
    createdAt: str
    trajectory: list[PocTrajectoryIteration]
    diary: PocDiary
    reviews: PocReviewsBundle
    strengths: StrengthOutput
    trace: PocRunTrace


_TRAJECTORY_LENGTH = 3

# services/poc_strength/fan_in.pyのREVIEWER_LABELSのキー集合と一致していることを
# tests/unit/test_poc_strength.pyで検知している。schemas/はservices/を参照しない
# 方針(依存の向きを保つ)のため値を複製しており、一方を変更した場合はもう一方も同期させること。
_REQUIRED_REVIEWER_KEYS = frozenset({"alpha", "beta", "gamma"})


class PocDiaryImport(BaseModel):
    """外部投入run用の日報。`mentorComment`はサーバー側がFan-in結果で補完するため
    受け取らない(`PocDiary`との違い)。
    """

    date: NonEmptyText
    tasks: list[PocDiaryTask] = Field(min_length=1)
    feelings: PocDiaryFeelings
    kpt: PocDiaryKpt


class PocRunImportTrace(BaseModel):
    """外部投入run用のtrace入力。`analysisProvider`はサーバー側が確定させるため受け取らない。"""

    generationProvider: NonEmptyText
    agents: list[PocRunAgentTrace] = Field(default_factory=list)


class PocRunImportRequest(BaseModel):
    """外部(Claude Codeセッション等)で生成したrun一式の投入リクエスト(POST /api/poc/runs/import)。

    !NOTE: アプリ実行時にLLMを呼ぶ経路は無い(`services/poc_strength/providers.py`参照)ため、
           生成(①ループ×3・②日報・③レビュー×3)は呼び出し側が担い、本APIはFan-in統合以降
           (③Fan-in・④解析・永続化)だけを引き受ける。台本経由の`POST /runs`と同じ
           `pipeline._assemble_run()`を通るため、解析ロジック自体は共有する。
    """

    personaKey: NonEmptyText = "external_claude"
    subjectId: NonEmptyText
    label: NonEmptyText
    injectedPersona: str | None = None
    trajectory: list[PocTrajectoryIteration]
    diary: PocDiaryImport
    reviews: list[PocReviewComment]
    trace: PocRunImportTrace
    externalStrengths: StrengthOutput | None = None

    @field_validator("trajectory")
    @classmethod
    def _validate_trajectory_covers_three_sequential_iterations(
        cls, value: list[PocTrajectoryIteration]
    ) -> list[PocTrajectoryIteration]:
        """仕様書§5「3回固定」。周回数・番号がずれたrunは解析の前提が崩れるため422で弾く。"""
        if len(value) != _TRAJECTORY_LENGTH:
            raise ValueError(f"trajectory must have exactly {_TRAJECTORY_LENGTH} iterations")
        if [item.iteration for item in value] != list(range(1, _TRAJECTORY_LENGTH + 1)):
            raise ValueError("trajectory iterations must be sequential starting from 1")
        return value

    @field_validator("reviews")
    @classmethod
    def _validate_reviews_cover_exactly_three_roles(
        cls, value: list[PocReviewComment]
    ) -> list[PocReviewComment]:
        """仕様書§3の3職種(alpha/beta/gamma)が過不足なく揃っていないとFan-inが機能しない。"""
        keys = [item.agentKey for item in value]
        if len(keys) != len(_REQUIRED_REVIEWER_KEYS) or set(keys) != _REQUIRED_REVIEWER_KEYS:
            raise ValueError(f"reviews must cover exactly {sorted(_REQUIRED_REVIEWER_KEYS)}")
        return value
