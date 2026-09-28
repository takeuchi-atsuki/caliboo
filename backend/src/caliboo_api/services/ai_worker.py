"""アプリ稼働中に永続ジョブを処理する。生成・承認・配信を分離する。"""

import asyncio
import logging
import time

from fastapi import HTTPException
from sqlalchemy.dialects.sqlite import insert

from caliboo_api.data.account_data import now_iso
from caliboo_api.data.assignment_proposal_data import save_generated_proposal
from caliboo_api.data.job_execution import claim_next, record_failure
from caliboo_api.data.proposal_extensions import today_jst
from caliboo_api.db import session_scope
from caliboo_api.extension_models import AgentJobExecution, ProposalAutomation
from caliboo_api.routers.development import complete_strength_result, pending_job
from caliboo_api.routers.proposal_agent import complete_proposal_result
from caliboo_api.services import job_inference, llm
from caliboo_api.services.assignment_proposal.llm_provider import LLMProposalGenerator

logger = logging.getLogger(__name__)


def process_next(config: llm.LLMSettings) -> bool:
    claim = claim_next(int(config.timeout * 2 + 30))
    if claim is None:
        return False
    try:
        output = job_inference.generate(claim.kind, claim.materials, claim.context, config)
        with session_scope() as session:
            # !NOTE: 期限とトークンを検証するUPDATEで書込権を確保し、結果と同時にcommitする。
            owned = session.query(AgentJobExecution).filter(
                AgentJobExecution.job_id == claim.id, AgentJobExecution.lease_token == claim.token,
                AgentJobExecution.leased_until > int(time.time()),
            ).update(dict(lease_token=None, leased_until=0, next_attempt_at=0, last_error=None),
                     synchronize_session=False)
            if not owned:
                return True
            if claim.kind == "strength":
                complete_strength_result(claim.id, output, session)
            elif claim.kind == "proposal":
                complete_proposal_result(claim.id, output, session)
            else:
                job = pending_job(session, claim.id, "proposal_initial")
                today = today_jst()
                automation = session.get(ProposalAutomation, job.user_id)
                if automation is not None and automation.last_date == today:
                    job.status = "superseded"
                else:
                    proposal, is_new = save_generated_proposal(
                        session, job.user_id, output, LLMProposalGenerator(config).name)
                    job.status = "completed"
                    job.completed_at = now_iso()
                    job.result = dict(proposalId=proposal.id, created=is_new)
                    session.execute(insert(ProposalAutomation).values(
                        user_id=job.user_id, last_date=today).on_conflict_do_update(
                        index_elements=["user_id"], set_={"last_date": today}))
                session.commit()
    except llm.LLMError as error:
        record_failure(claim, error.code, retryable=error.code == "provider_unavailable")
    except HTTPException as error:
        record_failure(claim, "stale_job" if error.status_code == 409 else "invalid_result",
                       superseded=error.status_code == 409)
    except (ValueError, TypeError, KeyError):
        record_failure(claim, "invalid_materials")
    return True


async def run_worker(stop: asyncio.Event, config: llm.LLMSettings) -> None:
    while not stop.is_set():
        try:
            worked = await asyncio.to_thread(process_next, config)
        except Exception:
            # !NOTE: 原文や認証情報を含む可能性がある例外文字列をログへ出さない。
            logger.error("AI worker could not process a job; lease recovery will retry it")
            worked = False
        if not worked:
            try:
                await asyncio.wait_for(stop.wait(), timeout=1)
            except TimeoutError:
                pass
