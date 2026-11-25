"""ホーム・強み・ジョブ一覧の取得件数と従来のAPI契約の回帰確認。"""

import time

from sqlalchemy import event

from caliboo_api.db import session_scope
from caliboo_api.extension_models import (
    AgentJob, AgentJobExecution, StrengthCandidate, StrengthInterpretation,
)

JOB_STATUSES = ("pending", "failed", "completed", "superseded")
CANDIDATE_STATUSES = ("approved", "pending", "rejected", "superseded")


def add_jobs(user_id, indices, kind="strength"):
    """解釈・実行状態の有無、各ステータスを含む架空の履歴を追加する。"""
    jobs = {}
    candidates = {}
    with session_scope() as session:
        for index in indices:
            job = AgentJob(
                user_id=user_id, kind=kind, fingerprint=f"fixture-{user_id}-{kind}-{index}",
                status=JOB_STATUSES[index % 4], materials={}, created_at="2026-10-01T00:00:00Z",
            )
            session.add(job)
            session.flush()
            jobs[index] = job.id
            if index % 5:
                session.add(AgentJobExecution(
                    job_id=job.id, attempts=2, last_error="fixture-error",
                    next_attempt_at=123, leased_until=int(time.time()) + 3600,
                ))
            if kind == "strength":
                candidate = StrengthCandidate(
                    user_id=user_id, job_id=job.id, status=CANDIDATE_STATUSES[index % 4],
                    label=f"候補 {index}", skill_code=f"TEST-{index}", confidence=80,
                    evidence=[], growth_action=f"確認 {index}",
                )
                session.add(candidate)
                session.flush()
                candidates[index] = candidate.id
                if index % 3:
                    session.add(StrengthInterpretation(
                        candidate_id=candidate.id, kind="work_style", summary=f"説明 {index}",
                        scope_note=f"範囲 {index}",
                    ))
        session.commit()
    return jobs, candidates


def get_with_sql(client, path):
    """対象APIの応答と、認証も含めた全SQL文の件数を数える。"""
    with session_scope() as session:
        engine = session.get_bind()
    statements = []

    def record(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        response = client.get(path)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert response.status_code == 200, response.text
    return response.json(), len(statements)


def test_strength_reads_keep_query_count_constant(client, admin_client, other_member_client):
    user_id = client.get("/api/auth/me").json()["id"]
    other_id = other_member_client.get("/api/auth/me").json()["id"]
    member_path = "/api/development/strengths"
    admin_path = f"{member_path}?userId={user_id}"
    jobs_path = "/api/development/jobs"

    def snapshot():
        reads = [get_with_sql(client, "/api/home/summary"), get_with_sql(client, member_path),
                 get_with_sql(admin_client, admin_path), get_with_sql(admin_client, jobs_path)]
        return [data for data, _count in reads], [count for _data, count in reads]

    empty, empty_counts = snapshot()
    assert not empty[0]["strengths"]
    assert empty[1] == {"candidates": [], "jobs": [], "reviewPending": False}
    assert empty[2] == empty[1]
    assert not empty[3]["jobs"]
    first_jobs, first_candidates = add_jobs(user_id, range(1))
    small, small_counts = snapshot()
    assert [row["id"] for row in small[1]["candidates"]] == list(first_candidates.values())
    assert [row["id"] for row in small[1]["jobs"]] == list(first_jobs.values())
    jobs, candidates = add_jobs(user_id, range(1, 26))
    jobs.update(first_jobs)
    candidates.update(first_candidates)
    other_jobs, other_candidates = add_jobs(other_id, range(2))
    proposals, _no_candidates = add_jobs(user_id, range(2), kind="proposal")
    large, large_counts = snapshot()
    # 候補・実行状態の件数を増やしても追加SELECTを発行してはならない。
    assert empty_counts == small_counts == large_counts == [7, 6, 6, 4]

    home, member, admin, inbox = large
    approved = list(range(24, -1, -4))
    assert [row["label"] for row in home["strengths"]] == [f"候補 {i}" for i in approved]
    assert home["strengths"][0] == dict(
        label="候補 24", tone="green", kind="ability", summary="", scopeNote="",
        evidence=[], growthAction="確認 24",
    )
    assert home["strengths"][1]["kind"] == "work_style"
    assert home["strengths"][1]["summary"] == "説明 20"
    assert [row["id"] for row in member["candidates"]] == [candidates[i] for i in approved]
    assert all(row["status"] == "approved" and row["userId"] == user_id
               for row in member["candidates"])
    assert [row["id"] for row in admin["candidates"]] == [candidates[i] for i in range(25, -1, -1)]
    assert member["reviewPending"] is True and admin["reviewPending"] is True
    assert member["jobs"] == admin["jobs"]
    assert [row["id"] for row in member["jobs"]] == [jobs[i] for i in range(25, 5, -1)]
    assert member["candidates"][0] == dict(
        id=candidates[24], userId=user_id, jobId=jobs[24], label="候補 24", skillCode="TEST-24",
        confidence=80, evidence=[], growthAction="確認 24", status="approved", decidedAt=None,
        kind="ability", summary="", scopeNote="",
    )
    assert {key: member["candidates"][1][key] for key in ("kind", "summary", "scopeNote")} == {
        "kind": "work_style", "summary": "説明 20", "scopeNote": "範囲 20",
    }
    assert member["jobs"][0] == dict(
        id=jobs[25], userId=user_id, kind="strength", status="failed",
        createdAt="2026-10-01T00:00:00Z", completedAt=None,
    )
    assert member["jobs"][1] == dict(
        id=jobs[24], userId=user_id, kind="strength", status="pending",
        createdAt="2026-10-01T00:00:00Z", completedAt=None, attempts=2,
        lastError="fixture-error", nextAttemptAt=123, processing=True,
    )
    expected_inbox_ids = sorted([jobs[i] for i in range(26) if i % 4 in (0, 1)]
                                + list(other_jobs.values()) + list(proposals.values()))
    assert [row["id"] for row in inbox["jobs"]] == expected_inbox_ids
    by_id = {row["id"]: row for row in inbox["jobs"]}
    assert by_id[jobs[24]] == member["jobs"][1]
    assert by_id[jobs[21]]["processing"] is False
    assert by_id[proposals[1]]["kind"] == "proposal"

    # 講師は他の本人の全候補を参照できるが、本人は他者の候補もジョブ一覧も参照できない。
    assert [row["id"] for row in admin_client.get(f"{member_path}?userId={other_id}").json()[
        "candidates"]] == [other_candidates[1], other_candidates[0]]
    assert client.get(f"{member_path}?userId={other_id}").status_code == 403
    assert client.get(jobs_path).status_code == 403
    assert other_member_client.get(admin_path).status_code == 403
    assert client.get(admin_path).json() == member

    # 再取得で更新を反映し、旧状態をキャッシュしないことを確認する。
    with session_scope() as session:
        session.get(AgentJobExecution, jobs[24]).leased_until = 0
        session.get(StrengthCandidate, candidates[25]).status = "approved"
        session.commit()
    refreshed = client.get(member_path).json()
    assert refreshed["jobs"][1]["processing"] is False
    assert refreshed["candidates"][0]["id"] == candidates[25]
    assert client.get("/api/home/summary").json()["strengths"][0]["label"] == "候補 25"
