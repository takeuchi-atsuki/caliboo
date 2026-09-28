"""課題案生成のオーケストレーション(`services/poc_strength/pipeline.py`の構成を踏襲)。

DBアクセス(`data/assignment_proposal_data.py`)が集めた日報・提出状況・フィードバックを
受け取り、設定に応じた生成器を呼び出す薄い層。既定はルールベースとし、
明示設定時だけ外部生成器を選ぶ。データ収集側は生成器を直接importしない。
"""

from .providers import RECENT_REPORT_COUNT, ProposalGenerator, RuleBasedProposalGenerator
from .llm_provider import LLMProposalGenerator
from caliboo_api.services import llm

__all__ = ["RECENT_REPORT_COUNT", "generate_proposal", "generator_name"]

# !NOTE: 具象クラスではなくProtocolで型注釈するのは、差し替え先がインターフェースを
#        満たしているかを静的検査で確かめられるようにするため(services/poc_strength/pipeline.py
#        と同じ理由)。
_PROPOSAL_GENERATOR: ProposalGenerator = RuleBasedProposalGenerator()


def current_generator() -> ProposalGenerator:
    if llm.provider_name() == "openai":
        return LLMProposalGenerator(llm.settings())
    return _PROPOSAL_GENERATOR


def generate_proposal(
    *,
    member_name: str,
    reports: list[dict],
    submission_statuses: list[str],
    feedbacks: list[dict],
    excluded_themes: set[str],
) -> dict:
    return current_generator().generate(
        member_name=member_name,
        reports=reports,
        submission_statuses=submission_statuses,
        feedbacks=feedbacks,
        excluded_themes=excluded_themes,
    )


def generator_name() -> str:
    """現在使用中の生成器のprovider名(`AssignmentProposal.generator`に保存する値)。"""
    return current_generator().name
