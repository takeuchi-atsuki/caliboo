"""プラガブルなLLM抽象化層(仕様書§6)。

worker/trainer/reviewの「生成」とanalysisの「解析」を、それぞれ差し替え可能な
インターフェース(`GenerationProvider`/`AnalysisProvider`)の背後に置く。

!NOTE: 本PoCではこのdevcontainerに`claude` CLIバイナリが存在せず、実行時に外部LLMや
       Claude Code CLIを呼び出す経路が無いため、`AuthoredMockProvider`は開発時に
       Claudeがペルソナ別に執筆した台本(`data/poc_persona_scripts.py`)をそのまま返す。
       将来実LLM(Claude Agent SDK等)に差し替える場合は、この2つのインターフェースの
       実装を追加するだけで済む。
"""

from typing import Protocol

from . import analysis as analysis_module


class GenerationProvider(Protocol):
    name: str

    def worker_output(self, script: dict, iteration_index: int) -> str: ...

    def trainer_feedback(self, script: dict, iteration_index: int) -> str: ...

    def diary_narrative(self, script: dict) -> dict: ...

    def review(self, script: dict, agent_key: str) -> dict: ...


class AnalysisProvider(Protocol):
    name: str

    def analyze(
        self,
        *,
        subject_id: str,
        run_id: str,
        trajectory: list[dict],
        diary: dict,
        reviews: list[dict],
        generated_at: str,
    ) -> dict: ...


class AuthoredMockProvider:
    """開発時にClaudeが執筆した台本をそのまま返すモックプロバイダ。"""

    name = "authored_mock_v1"

    def worker_output(self, script: dict, iteration_index: int) -> str:
        return script["iterations"][iteration_index]["workerOutput"]

    def trainer_feedback(self, script: dict, iteration_index: int) -> str:
        return script["iterations"][iteration_index]["trainerFeedback"]

    def diary_narrative(self, script: dict) -> dict:
        diary = script["diary"]
        return {
            "date": diary["date"],
            "tasks": [dict(task) for task in diary["tasks"]],
            "feelings": dict(diary["feelings"]),
            "kpt": dict(diary["kpt"]),
        }

    def review(self, script: dict, agent_key: str) -> dict:
        for review in script["reviews"]:
            if review["agentKey"] == agent_key:
                return dict(review)
        raise KeyError(agent_key)


class RuleBasedAnalysisProvider:
    """決定論的なルールベース解析エンジン(`analysis.py`)のプロバイダラッパー。"""

    name = "rule_based_v1"

    def analyze(
        self,
        *,
        subject_id: str,
        run_id: str,
        trajectory: list[dict],
        diary: dict,
        reviews: list[dict],
        generated_at: str,
    ) -> dict:
        return analysis_module.analyze(
            subject_id=subject_id,
            run_id=run_id,
            trajectory=trajectory,
            diary=diary,
            reviews=reviews,
            generated_at=generated_at,
            provider_name=self.name,
        )
