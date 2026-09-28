"""日報提出イベントと課題案エージェントの接続。"""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from caliboo_api.data.account_data import is_active
from caliboo_api.data.assignment_data import fetch_visible_assignment_statuses
from caliboo_api.data.assignment_proposal_data import create_or_get_pending_proposal
from caliboo_api.data.assignment_proposal_data import _find_pending_proposal, proposal_inputs
from caliboo_api.data.agent_jobs import create_job
from caliboo_api.extension_models import AgentJob, ProposalAutomation
from caliboo_api.services.llm import LLMError, provider_name


def today_jst() -> str:
    return datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()


def enqueue_proposal(session: Session, user_id: int) -> AgentJob | None:
    today = today_jst()
    session.execute(insert(ProposalAutomation).values(user_id=user_id, last_date="").
                    on_conflict_do_nothing())
    automation = session.get(ProposalAutomation, user_id)
    if automation.last_date == today or _find_pending_proposal(session, user_id) is not None:
        session.commit()
        return None
    inputs = proposal_inputs(session, user_id)
    if not inputs["reports"] and not inputs["feedbacks"]:
        session.commit()
        return None
    job = create_job(session, user_id, "proposal_initial", {"inputs": inputs, "date": today})
    session.query(AgentJob).filter(
        AgentJob.user_id == user_id, AgentJob.kind == "proposal_initial", AgentJob.id < job.id,
        AgentJob.status.in_(["pending", "failed"]),
    ).update({"status": "superseded"}, synchronize_session=False)
    session.commit()
    return job


def auto_propose(session: Session, user_id: int, event: str = "report") -> None:
    if not is_active(session, user_id):
        return
    if provider_name() == "openai":
        enqueue_proposal(session, user_id)
        return
    if event != "report":
        return
    statuses = fetch_visible_assignment_statuses(session, user_id)
    if statuses.count("not_submitted") < 3:
        return
    today = today_jst()
    session.execute(insert(ProposalAutomation).values(user_id=user_id, last_date="").
                    on_conflict_do_nothing())
    updated = session.query(ProposalAutomation).filter(
        ProposalAutomation.user_id == user_id, ProposalAutomation.last_date != today,
    ).update({"last_date": today})
    session.commit()
    if updated:
        try:
            create_or_get_pending_proposal(user_id)
        except LLMError:
            # !NOTE: 日報は既に保存済み。推論障害で提出まで失敗とせず、同日再試行を許す。
            session.query(ProposalAutomation).filter_by(user_id=user_id, last_date=today).update(
                {"last_date": ""})
            session.commit()
