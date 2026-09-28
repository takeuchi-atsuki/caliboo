"""PL-4/5: 取得権、障害復旧、古い結果、型と引用の境界。"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from caliboo_api.data.agent_jobs import create_job, enqueue_strength
from caliboo_api.data import job_execution as queue
from caliboo_api.data.proposal_extensions import auto_propose, today_jst
from caliboo_api.db import bootstrap_db, session_scope
from caliboo_api.extension_models import (
    AccountState, AgentJob, AgentJobExecution, ProposalAutomation, StrengthCandidate,
)
from caliboo_api.main import app
from caliboo_api.models import Assignment, AssignmentProposal, AssignmentSubmission
from caliboo_api.schemas.agent_jobs import StrengthResult
from caliboo_api.services import ai_worker, job_inference, llm
from caliboo_api.services.assignment_proposal.providers import RuleBasedProposalGenerator

CONFIG = llm.LLMSettings("test-model", "test-secret", 1)


def enqueue(user_id):
    with session_scope() as session:
        return enqueue_strength(session, user_id).id


def basic_job(user_id, kind="strength", materials=None):
    with session_scope() as session:
        job = create_job(session, user_id, kind, materials or {"sources": []})
        session.commit()
        return job.id


def candidate_batch(materials, **changes):
    source = next(item for item in materials["sources"] if item["evidenceEligible"])
    candidate = dict(label="根拠を確認する力", skillCode="TEST", confidence=70,
                     growthAction="確認した観点を共有する", evidence=[dict(
                         materialId=source["id"], quote=source["text"])])
    return job_inference.CandidateBatch(candidates=[{**candidate, **changes}], notes="観測に基づく候補")


def fake_strength(instructions, inputs, output_type, config):
    assert "進捗" in instructions
    assert "user_id" not in inputs
    return candidate_batch(inputs["materials"])


def get_state(job_id):
    with session_scope() as session:
        job = session.get(AgentJob, job_id)
        execution = session.get(AgentJobExecution, job_id)
        return job.status, execution.attempts, execution.last_error


def test_progress_context_changes_fingerprint_and_old_jobs_still_work(user_ids):
    user_id = user_ids["yuki"]
    first = enqueue(user_id)
    assert enqueue(user_id) == first
    with session_scope() as session:
        session.add(Assignment(title="追加", body="練習", created_at="2026-09-29"))
        session.commit()
    second = enqueue(user_id)
    assert second > first
    with session_scope() as session:
        assert session.get(AgentJob, first).status == "superseded"
        assert "progress" not in session.get(AgentJob, second).materials
    claim = queue.claim_next(30)
    assert claim.context["progress"]["not_submitted"] == 2
    queue.record_failure(claim, "test")
    legacy = basic_job(user_id, materials={"sources": [], "legacy": True})
    assert queue.claim_next(30).context == {}
    assert get_state(legacy)[0] == "pending"


def test_claim_is_exclusive_recovers_and_ignores_old_failure(user_ids, monkeypatch):
    job_id = basic_job(user_ids["yuki"])
    now = [1000]
    monkeypatch.setattr(queue.time, "time", lambda: now[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(queue.claim_next, [30, 30]))
    first = next(claim for claim in claims if claim is not None)
    assert len([claim for claim in claims if claim]) == 1
    assert queue.claim_next(30) is None
    now[0] += 31
    second = queue.claim_next(30)
    assert second.token != first.token and second.id == job_id
    queue.record_failure(first, "late-error")
    assert get_state(job_id) == ("pending", 2, None)
    now[0] += 31
    assert queue.claim_next(30) is not None
    now[0] += 31
    assert queue.claim_next(30) is None
    assert get_state(job_id) == ("failed", 3, "lease_expired")


def test_disabled_member_is_not_claimed(user_ids):
    job_id = basic_job(user_ids["yuki"])
    with session_scope() as session:
        session.get(AccountState, user_ids["yuki"]).active = False
        session.commit()
    assert queue.claim_next(30) is None
    with session_scope() as session:
        assert session.get(AgentJob, job_id).status == "pending"


def test_strength_inference_saves_one_pending_candidate(user_ids, monkeypatch):
    job_id = enqueue(user_ids["yuki"])
    monkeypatch.setattr(llm, "generate_json", fake_strength)
    assert ai_worker.process_next(CONFIG)
    assert not ai_worker.process_next(CONFIG)
    bootstrap_db()
    with session_scope() as session:
        job = session.get(AgentJob, job_id)
        assert job.status == "completed"
        assert job.result["trace"]["provider"] == "openai"
        assert job.result["trace"]["model"] == "test-model"
        rows = session.query(StrengthCandidate).filter_by(job_id=job_id).all()
        assert len(rows) == 1 and rows[0].status == "pending"
        assert rows[0].evidence[0]["source"]["evidenceEligible"] is True


@pytest.mark.parametrize("mode", ["wrong_quote", "duplicate", "invalid_materials"])
def test_invalid_output_never_publishes(user_ids, monkeypatch, mode):
    job_id = enqueue(user_ids["yuki"])

    def generate(instructions, inputs, output_type, config):
        batch = candidate_batch(inputs["materials"])
        if mode == "wrong_quote":
            batch.candidates[0].evidence[0].quote = "存在しない原文"
        else:
            batch.candidates.append(batch.candidates[0])
        return batch

    monkeypatch.setattr(llm, "generate_json", generate)
    if mode == "invalid_materials":
        with session_scope() as session:
            session.get(AgentJob, job_id).materials = {"schemaVersion": "future", "sources": []}
            session.commit()
    assert ai_worker.process_next(CONFIG)
    assert get_state(job_id)[0] == "failed"
    with session_scope() as session:
        assert session.query(StrengthCandidate).filter_by(job_id=job_id).count() == 0


def test_transport_backoff_exhaustion_and_restart(user_ids, monkeypatch):
    job_id = enqueue(user_ids["yuki"])
    now = [1000]
    monkeypatch.setattr(queue.time, "time", lambda: now[0])

    def fail(kind, materials, context, config):
        raise llm.LLMError("provider_unavailable")

    monkeypatch.setattr(job_inference, "generate", fail)
    for attempt, delay in [(1, 5), (2, 30), (3, 0)]:
        assert ai_worker.process_next(CONFIG)
        assert get_state(job_id)[1] == attempt
        assert not ai_worker.process_next(CONFIG)
        now[0] += delay
        bootstrap_db()
    assert get_state(job_id) == ("failed", 3, "provider_unavailable")


@pytest.mark.parametrize("mode", ["superseded", "disabled", "expired"])
def test_result_after_change_is_discarded(user_ids, monkeypatch, mode):
    user_id = user_ids["yuki"]
    job_id = enqueue(user_id)

    def generate(kind, materials, context, config):
        with session_scope() as session:
            if mode == "superseded":
                session.get(AgentJob, job_id).status = "superseded"
            elif mode == "disabled":
                session.get(AccountState, user_id).active = False
            else:
                session.get(AgentJobExecution, job_id).leased_until = 0
            session.commit()
        return StrengthResult(trace=dict(provider="openai", model="test", promptVersion="test"),
                              **candidate_batch(materials).model_dump())

    monkeypatch.setattr(job_inference, "generate", generate)
    assert ai_worker.process_next(CONFIG)
    with session_scope() as session:
        assert session.query(StrengthCandidate).filter_by(job_id=job_id).count() == 0
        assert session.get(AgentJob, job_id).status != "completed"


def test_initial_proposal_uses_snapshot_and_daily_success_limit(user_ids, monkeypatch):
    user_id = user_ids["yuki"]
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    with session_scope() as session:
        auto_propose(session, user_id)
        job = session.query(AgentJob).filter_by(kind="proposal_initial").one()
        job_id = job.id
        inputs = job.materials["inputs"]
    result = RuleBasedProposalGenerator().generate(member_name="", **{
        **inputs, "excluded_themes": set(inputs["excluded_themes"])})
    monkeypatch.setattr(job_inference, "generate", lambda kind, materials, context, config: result)
    assert ai_worker.process_next(CONFIG)
    assert get_state(job_id)[0] == "completed"
    with session_scope() as session:
        assert session.query(AssignmentProposal).filter_by(target_user_id=user_id).count() == 1
        assert session.get(ProposalAutomation, user_id).last_date == today_jst()
        auto_propose(session, user_id)
        assert session.query(AgentJob).filter_by(kind="proposal_initial").count() == 1
        extra = create_job(session, user_id, "proposal_initial", {"inputs": inputs, "extra": 1})
        extra_id = extra.id
        session.commit()
    assert ai_worker.process_next(CONFIG)
    assert get_state(extra_id)[0] == "superseded"


def test_worker_loop_recovers_unexpected_errors_and_stops(monkeypatch):
    async def scenario():
        stop = asyncio.Event()
        count = [0]

        def process(config):
            count[0] += 1
            if count[0] == 1:
                raise RuntimeError("secret details")
            stop.set()
            return True

        monkeypatch.setattr(ai_worker, "process_next", process)
        await ai_worker.run_worker(stop, CONFIG)
        assert count[0] == 2

    asyncio.run(scenario())


def test_lifespan_starts_configured_worker_and_waits_for_stop(tmp_path, monkeypatch):
    monkeypatch.setenv("CALIBOO_AI_PROVIDER", "openai")
    monkeypatch.setenv("CALIBOO_AI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("CALIBOO_SQLITE_PATH", str(tmp_path / "lifecycle.db"))
    states = []

    async def run(stop, config):
        states.append(config.model)
        await stop.wait()
        states.append("stopped")

    monkeypatch.setattr(ai_worker, "run_worker", run)
    with TestClient(app):
        assert states == ["test-model"]
    assert states == ["test-model", "stopped"]


@pytest.mark.parametrize("kind,materials,code", [
    ("proposal", {"sources": []}, "insufficient_materials"),
    ("unknown", {}, "unsupported_job"),
])
def test_inference_rejects_unusable_jobs(kind, materials, code):
    with pytest.raises(llm.LLMError) as caught:
        job_inference.generate(kind, materials, {}, CONFIG)
    assert caught.value.code == code


def test_new_feedback_timestamp_supersedes_failed_snapshot(user_ids):
    user_id = user_ids["yuki"]
    first = enqueue(user_id)
    claim = queue.claim_next(30)
    queue.record_failure(claim, "invalid_output")
    with session_scope() as session:
        row = session.query(AssignmentSubmission).filter(
            AssignmentSubmission.user_id == user_id,
            AssignmentSubmission.feedback_comment.is_not(None)).first()
        row.feedback_at = "2026-09-29T10:00:00+00:00"
        session.commit()
    second = enqueue(user_id)
    assert second != first
    with session_scope() as session:
        assert session.get(AgentJob, first).status == "superseded"
        materials = session.get(AgentJob, second).materials
        feedback = next(item for item in materials["sources"] if item["field"] == "feedback")
        assert feedback["date"] == "2026-09-29T10:00:00+00:00"
