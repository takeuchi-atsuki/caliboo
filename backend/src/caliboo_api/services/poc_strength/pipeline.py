"""強み解析PoCのオーケストレーション(仕様書§5のパイプラインを1 runで通す)。

台本経由(`run_pipeline`)と外部投入経由(`import_run`)の2つの入口を持つ。

台本経由: ①ペルソナ台本から3周のtrajectoryを組み立て → ②日報を集約 → ③3職種レビュー
→ Fan-in → ④解析エンジン呼び出し、の順に実行する。

外部投入経由: Claude Codeセッション等が①②③(生成)を担い、組み立て済みのtrajectory・
日報・レビューを受け取る。Fan-in以降(③Fan-in → ④解析)は台本経由と同じ`_assemble_run()`
を通る(仕様書§2「アプリ実行時にLLMを呼ぶ経路は無いが、開発セッションのClaudeが生成を担い
投入する経路を持つ」。詳細は`docs/architecture.md`)。

!NOTE: 台本経由の生成が事前執筆コンテンツ+決定論的解析のため一瞬で終わる。仕様書§6が想定する
       非同期ジョブ化(ポーリング/webhook)は本PoCの規模ではオーバーエンジニアリングと
       判断し、runは同期実行にとどめる(呼び出し側のAPIは常に完了済みのrunを返す)。
"""

from datetime import datetime, timezone

from caliboo_api.data import poc_persona_scripts

from . import fan_in
from .providers import (
    AnalysisProvider,
    AuthoredMockProvider,
    GenerationProvider,
    RuleBasedAnalysisProvider,
)

# !NOTE: 具象クラスではなくProtocolで型注釈するのは、差し替え先が
#        インターフェースを満たしているかを静的検査で確かめられるようにするため
#        (注釈が具象型だと、抽象化層が名前だけのものになる)。
_GENERATION_PROVIDER: GenerationProvider = AuthoredMockProvider()
_ANALYSIS_PROVIDER: AnalysisProvider = RuleBasedAnalysisProvider()


class UnknownPersonaError(Exception):
    """未知のpersonaKeyが指定された場合に送出する。"""


def list_personas() -> list[dict]:
    return [
        {
            "personaKey": script["personaKey"],
            "label": script["label"],
            "description": script["description"],
        }
        for script in poc_persona_scripts.PERSONA_SCRIPTS
    ]


def _build_trajectory(script: dict) -> list[dict]:
    trajectory = []
    for index, item in enumerate(script["iterations"]):
        task = item["task"]
        trajectory.append(
            {
                "iteration": index + 1,
                "task": {
                    "taskId": task["taskId"],
                    "title": task["title"],
                    "description": task["description"],
                    "skillHint": task["skillHint"],
                },
                "workerOutput": _GENERATION_PROVIDER.worker_output(script, index),
                "trainerFeedback": _GENERATION_PROVIDER.trainer_feedback(script, index),
                "humanOverride": None,
            }
        )
    return trajectory


def _build_reviews_from_script(script: dict) -> list[dict]:
    return [
        _GENERATION_PROVIDER.review(script, review["agentKey"]) for review in script["reviews"]
    ]


def _assemble_run(
    *,
    persona_key: str,
    subject_id: str,
    label: str,
    injected_persona: str | None,
    trajectory: list[dict],
    diary: dict,
    reviews: list[dict],
    trace: dict,
) -> dict:
    """trajectory・日報(mentorComment抜き)・レビューからrun一式を組み立てる共通処理。

    Fan-in統合 →`diary.mentorComment`の補完 → 解析エンジン呼び出し、の順序を
    台本経由(`run_pipeline`)・外部投入経由(`import_run`)の両方で1か所に集約する。

    戻り値の`strengths.runId`は空文字のまま返す(DBへの保存後にrun_idが確定するため、
    呼び出し側の`data/poc_strength_data.py`が補完する)。

    !NOTE: `trace`は`analysisProvider`以外を呼び出し側が組み立てる。生成の由来
           (台本の`scriptVersion` or 外部エージェントの`agents`)が経路によって
           異なり、共通化できるのは実際に呼び出す解析プロバイダの名前だけであるため。
    """
    fan_in_result = fan_in.merge_reviews(reviews)
    reviews_bundle = {"reviews": reviews, **fan_in_result}
    diary_with_comment = {**diary, "mentorComment": fan_in_result["fanInComment"]}

    generated_at = datetime.now(timezone.utc).isoformat()
    strengths = _ANALYSIS_PROVIDER.analyze(
        subject_id=subject_id,
        run_id="",
        trajectory=trajectory,
        diary=diary_with_comment,
        reviews=reviews,
        generated_at=generated_at,
    )

    return {
        "personaKey": persona_key,
        "subjectId": subject_id,
        "label": label,
        "injectedPersona": injected_persona,
        "trajectory": trajectory,
        "diary": diary_with_comment,
        "reviews": reviews_bundle,
        "strengths": strengths,
        "trace": {**trace, "analysisProvider": _ANALYSIS_PROVIDER.name},
    }


def run_pipeline(persona_key: str) -> dict:
    """persona_keyに対応する台本で全パイプラインを実行し、run一式を組み立てて返す。"""
    script = poc_persona_scripts.find_script(persona_key)
    if script is None:
        raise UnknownPersonaError(persona_key)

    trajectory = _build_trajectory(script)
    reviews = _build_reviews_from_script(script)
    diary = _GENERATION_PROVIDER.diary_narrative(script)

    return _assemble_run(
        persona_key=script["personaKey"],
        subject_id=script["subjectId"],
        label=script["label"],
        injected_persona=script["injectedPersona"],
        trajectory=trajectory,
        diary=diary,
        reviews=reviews,
        trace={
            "generationProvider": _GENERATION_PROVIDER.name,
            "scriptVersion": poc_persona_scripts.SCRIPT_VERSION,
        },
    )


def import_run(payload: dict) -> dict:
    """外部(Claude Codeセッション等)で生成したtrajectory・日報・レビューを受け取り、
    Fan-in統合以降(mentorComment補完・解析・永続化用run一式の組み立て)を実行する。

    `payload`は`schemas/poc_strength.py`の`PocRunImportRequest`をdict化したもの。
    `externalStrengths`が渡された場合は、ルールベース解析(`strengths`)とは別に
    `trace.externalAnalysis`へ格納する(別モデルによる独立解析。仕様書§2「評価者の分離」)。
    """
    trace: dict = {
        "generationProvider": payload["trace"]["generationProvider"],
        "agents": payload["trace"]["agents"],
    }
    external_strengths = payload.get("externalStrengths")
    if external_strengths is not None:
        trace["externalAnalysis"] = external_strengths

    return _assemble_run(
        persona_key=payload["personaKey"],
        subject_id=payload["subjectId"],
        label=payload["label"],
        injected_persona=payload.get("injectedPersona"),
        trajectory=payload["trajectory"],
        diary=payload["diary"],
        reviews=payload["reviews"],
        trace=trace,
    )
