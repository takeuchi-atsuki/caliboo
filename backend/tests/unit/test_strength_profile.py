"""承認済み観点: 解釈契約と、通常取込・自動worker・holdout共通の根拠検証。"""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text

from caliboo_api.data.agent_jobs import create_job
from caliboo_api.db import bootstrap_db, session_scope
from caliboo_api.extension_models import AgentJob, StrengthCandidate, StrengthInterpretation
from caliboo_api.models import User
from caliboo_api.schemas.agent_jobs import StrengthResult
from caliboo_api.services import ai_worker, job_inference, llm
from caliboo_api.services.strength_materials import normalize_strength_materials
from caliboo_api.services.strength_result import validate_evidence

TRACE = dict(provider="codex_agent", model="test", promptVersion="profile-test")


def materials():
    sources = [
        dict(id="report:1:keep", kind="report", field="keep", text="境界を確認した。",
             date="2026-09-27", evidenceEligible=True),
        dict(id="report:1:problem", kind="report", field="problem", text="説明に困った。",
             date="2026-09-27", evidenceEligible=False),
        dict(id="submission:2:answer", kind="submission", field="answer",
             text="結果を照合した。", date="2026-09-28", evidenceEligible=True),
        dict(id="submission:2:feedback", kind="submission", field="feedback",
             text="丁寧な確認。", date="2026-09-28", evidenceEligible=True),
        dict(id="submission:3:feedback", kind="submission", field="feedback",
             text="追加の所見。", date="2026-09-29", evidenceEligible=True),
    ]
    return normalize_strength_materials({"sources": sources})


def evidence(*source_ids):
    sources = {source["id"]: source for source in materials()["sources"]}
    return [dict(materialId=source_id, quote=sources[source_id]["text"])
            for source_id in source_ids]


def candidate(kind="work_style", source_ids=("report:1:keep", "submission:2:answer")):
    return dict(kind=kind, skillCode="TEST", label="確かめながら進める",
                summary="異なる仕事で結果を照合した。", scopeNote="2件の記録で観測した範囲。",
                confidence=80, growthAction="別の課題でも試す", evidence=evidence(*source_ids))


def result(*candidates):
    return StrengthResult.model_validate(dict(trace=TRACE, candidates=list(candidates),
                                              notes="原文で確認した"))


def test_work_style_requires_interpretation_and_distinct_self_records():
    valid = candidate()
    assert validate_evidence(result(valid, candidate(kind="ability")), materials())
    for field in ("summary", "scopeNote"):
        invalid = {**valid, field: "  "}
        with pytest.raises(ValidationError):
            result(invalid)

    rejected = [
        ["report:1:keep", "report:1:keep"],
        ["submission:2:answer", "submission:2:feedback"],
        ["submission:2:feedback", "submission:2:feedback"],
        ["submission:2:feedback", "submission:3:feedback"],
        ["report:1:keep", "submission:3:feedback"],
        ["report:1:problem", "submission:2:answer"],
    ]
    for source_ids in rejected:
        with pytest.raises(HTTPException) as error:
            validate_evidence(result(candidate(source_ids=source_ids)), materials())
        assert error.value.status_code == 422
    with pytest.raises(HTTPException):
        validate_evidence(result(candidate(), candidate()), materials())
    invalid_quote = candidate()
    invalid_quote["evidence"][0]["quote"] = "原文にない達成"
    with pytest.raises(HTTPException):
        validate_evidence(result(invalid_quote), materials())


def test_automatic_worker_uses_shared_profile_contract(user_ids, monkeypatch):
    user_id = user_ids["yuki"]
    with session_scope() as session:
        job = create_job(session, user_id, "strength", materials())
        session.commit()
        job_id = job.id

    monkeypatch.setattr(job_inference, "generate", lambda kind, snapshot, context, config:
                        result(candidate()))
    assert ai_worker.process_next(llm.LLMSettings("test-model", "test-secret", 1))
    with session_scope() as session:
        assert session.get(AgentJob, job_id).status == "completed"
        row = session.query(StrengthCandidate).filter_by(job_id=job_id).one()
        interpretation = session.get(StrengthInterpretation, row.id)
        assert (interpretation.kind, interpretation.summary, interpretation.scope_note) == (
            "work_style", "異なる仕事で結果を照合した。", "2件の記録で観測した範囲。")

    with session_scope() as session:
        second = create_job(session, user_id, "strength", materials(), {"revision": 2})
        session.commit()
        second_id = second.id
    monkeypatch.setattr(job_inference, "generate", lambda kind, snapshot, context, config:
                        result(candidate(source_ids=["report:1:keep", "report:1:keep"])))
    assert ai_worker.process_next(llm.LLMSettings("test-model", "test-secret", 1))
    with session_scope() as session:
        assert session.get(AgentJob, second_id).status == "failed"
        assert session.query(StrengthCandidate).filter_by(job_id=second_id).count() == 0


def test_existing_database_gets_additional_interpretation_table(user_ids):
    # !NOTE: 既存DBへ旧テーブルのALTERを要求せず、新しいテーブルだけを作れることを確認する。
    with session_scope() as session:
        session.execute(text("DROP TABLE strength_interpretations"))
        session.commit()
    bootstrap_db()
    with session_scope() as session:
        assert session.execute(text("SELECT COUNT(*) FROM strength_interpretations")).scalar() == 0
        assert session.get(User, user_ids["yuki"]) is not None
