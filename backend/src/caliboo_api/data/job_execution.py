"""永続キューの期限付き取得権。推論中はDBトランザクションを保持しない。"""

import time
import uuid
from dataclasses import dataclass

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.sqlite import insert

from caliboo_api.db import session_scope
from caliboo_api.extension_models import AccountState, AgentJob, AgentJobContext, AgentJobExecution
from caliboo_api.models import User

MAX_ATTEMPTS = 3
JOB_KINDS = ("strength", "proposal", "proposal_initial")


@dataclass(frozen=True)
class ClaimedJob:
    id: int
    user_id: int
    kind: str
    materials: dict
    context: dict
    token: str


def claim_next(lease_seconds: int) -> ClaimedJob | None:
    now = int(time.time())
    with session_scope() as session:
        # !NOTE: 最終試行中にプロセスが落ちても、永久に「処理中」に残さない。
        exhausted = session.query(AgentJobExecution).join(
            AgentJob, AgentJob.id == AgentJobExecution.job_id).filter(
            AgentJob.status == "pending", AgentJobExecution.attempts >= MAX_ATTEMPTS,
            AgentJobExecution.leased_until <= now).all()
        for execution in exhausted:
            updated = session.query(AgentJob).filter_by(
                id=execution.job_id, status="pending").update({"status": "failed"})
            if updated:
                execution.lease_token = None
                execution.last_error = "lease_expired"
        session.flush()
        available = session.query(AgentJob).join(User, User.id == AgentJob.user_id).outerjoin(
            AccountState, AccountState.user_id == AgentJob.user_id).outerjoin(
            AgentJobExecution, AgentJobExecution.job_id == AgentJob.id).filter(
            AgentJob.status == "pending", AgentJob.kind.in_(JOB_KINDS), User.role == "member",
            or_(AccountState.user_id.is_(None), AccountState.active.is_(True)),
            or_(AgentJobExecution.job_id.is_(None), and_(
                AgentJobExecution.leased_until <= now, AgentJobExecution.next_attempt_at <= now)),
        ).order_by(AgentJob.id).limit(20).all()
        for job in available:
            session.execute(insert(AgentJobExecution).values(job_id=job.id).
                            on_conflict_do_nothing())
            token = uuid.uuid4().hex
            claimed = session.query(AgentJobExecution).filter(
                AgentJobExecution.job_id == job.id, AgentJobExecution.leased_until <= now,
                AgentJobExecution.next_attempt_at <= now,
                AgentJobExecution.attempts < MAX_ATTEMPTS,
                AgentJobExecution.job_id.in_(select(AgentJob.id).where(
                    AgentJob.status == "pending")),
            ).update(dict(lease_token=token, leased_until=now + lease_seconds,
                          attempts=AgentJobExecution.attempts + 1, last_error=None),
                     synchronize_session=False)
            if claimed:
                context = session.get(AgentJobContext, job.id)
                result = ClaimedJob(job.id, job.user_id, job.kind, job.materials,
                                    context.context if context is not None else {}, token)
                session.commit()
                return result
        session.commit()
        return None


def record_failure(claim: ClaimedJob, code: str, retryable: bool = False,
                   superseded: bool = False) -> None:
    now = int(time.time())
    with session_scope() as session:
        execution = session.get(AgentJobExecution, claim.id)
        if execution is None:
            return
        retry = retryable and execution.attempts < MAX_ATTEMPTS
        updated = session.query(AgentJobExecution).filter_by(
            job_id=claim.id, lease_token=claim.token).update(dict(
                lease_token=None, leased_until=0, last_error=code,
                next_attempt_at=now + (5 if execution.attempts == 1 else 30) if retry else 0,
            ), synchronize_session=False)
        if updated and (not retry or superseded):
            session.query(AgentJob).filter_by(id=claim.id, status="pending").update(
                {"status": "superseded" if superseded else "failed"})
        session.commit()
