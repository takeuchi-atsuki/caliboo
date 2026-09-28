"""強み解析入力契約: 原文・分類・互換性とエージェントexportの境界。"""

from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

from caliboo_api.data.agent_jobs import enqueue_strength
from caliboo_api.db import session_scope
from caliboo_api.models import Assignment, AssignmentSubmission, Report
from caliboo_api.schemas.strength_materials import StrengthAnalysisMaterials
from caliboo_api.services.strength_materials import normalize_strength_materials


def source(field="keep", record_id=1, **changes):
    kind = "submission" if field in {"answer", "feedback"} else "report"
    return dict(id=f"{kind}:{record_id}:{field}", kind=kind, field=field,
                text="  原文\r\nＡＢＣとe\u0301を照合した。\t", date="2026-09-28",
                evidenceEligible=field in {"keep", "answer", "feedback"}, **changes)


def test_normalization_preserves_original_and_distinguishes_six_roles():
    legacy = {"sources": [source(field) for field in
                          ("keep", "problem", "try", "moodComment", "answer", "feedback")]}
    before = deepcopy(legacy)
    materials = normalize_strength_materials(legacy)
    assert legacy == before
    assert materials["schemaVersion"] == "strength-materials.v1"
    assert [item["sourceRole"] for item in materials["sources"]] == [
        "self_report", "difficulty", "plan", "emotion", "work_product", "mentor_feedback",
    ]
    for original, normalized in zip(legacy["sources"], materials["sources"]):
        assert all(normalized[key] == value for key, value in original.items())
    assert normalize_strength_materials(materials) == materials


@pytest.mark.parametrize("changes", [
    {"text": ""}, {"text": " \r\n\t"}, {"text": None}, {"text": 42},
    {"date": None}, {"id": "report:0:keep"}, {"id": "submission:1:keep"},
    {"id": "report:1:try"}, {"id": "report:1:keep\n"}, {"kind": "submission"},
    {"field": "unknown"}, {"field": []}, {"sourceRole": "plan"},
    {"evidenceEligible": False}, {"evidenceEligible": "true"}, {"evidenceEligible": 1},
    {"unexpected": "value"},
])
def test_inconsistent_sources_are_rejected(changes):
    with pytest.raises(ValidationError):
        normalize_strength_materials({"sources": [{**source(), **changes}]})


@pytest.mark.parametrize("materials", [
    None, [], {}, {"sources": None}, {"sources": {}}, {"sources": [None]},
    {"sources": [source(), source()]}, {"sources": [], "unexpected": 1},
    {"schemaVersion": "strength-materials.v2", "sources": []},
    {"schemaVersion": None, "sources": []},
    {"schemaVersion": "strength-materials.v1", "sources": [source()]},
])
def test_malformed_or_unknown_contracts_are_rejected(materials):
    with pytest.raises(ValidationError):
        normalize_strength_materials(materials)


def test_missing_fields_are_not_invented():
    for field in source():
        incomplete = source()
        del incomplete[field]
        with pytest.raises(ValidationError):
            normalize_strength_materials({"sources": [incomplete]})
    assert normalize_strength_materials({"sources": []})["sources"] == []


def test_source_limit():
    sources = [source(record_id=index) for index in range(1, 121)]
    assert len(normalize_strength_materials({"sources": sources})["sources"]) == 120
    with pytest.raises(ValidationError):
        normalize_strength_materials({"sources": sources + [source(record_id=121)]})


def test_snapshot_limits_order_and_blank_omission(user_ids):
    with session_scope() as session:
        reports, submissions = [], []
        for index in range(21):
            report = Report(user_id=user_ids["yuki"], date="2026-09-28", keep=f"keep-{index}",
                            problem=" \n", try_="", mood=[], mood_comment="\t",
                            status="submitted", saved_at="2026-09-28")
            assignment = Assignment(title="課題", body="説明", created_at="2026-09-28")
            session.add_all([report, assignment])
            session.flush()
            submission = AssignmentSubmission(
                assignment_id=assignment.id, user_id=user_ids["yuki"],
                answer_text=f"answer-{index}", submitted_at="2026-09-28T12:00:00+00:00",
                feedback_comment=" " if index else None,
            )
            session.add(submission)
            session.flush()
            reports.append(report.id)
            submissions.append(submission.id)
        session.commit()
        materials = enqueue_strength(session, user_ids["yuki"]).materials
        assert [item["id"] for item in materials["sources"]] == [
            *[f"report:{item}:keep" for item in reversed(reports[1:])],
            *[f"submission:{item}:answer" for item in reversed(submissions[1:])],
        ]


def test_schema_endpoint_requires_admin(admin_client, client, anonymous_client):
    path = "/api/development/strength-materials/schema"
    assert anonymous_client.get(path).status_code == 401
    assert client.get(path).status_code == 403
    response = admin_client.get(path)
    assert response.status_code == 200
    schema = response.json()
    assert schema == StrengthAnalysisMaterials.model_json_schema()
    assert schema["properties"]["schemaVersion"]["const"] == "strength-materials.v1"
    assert schema["$defs"]["TrySource"]["properties"]["evidenceEligible"]["const"] is False


@pytest.mark.parametrize("kind", ["strength", "proposal"])
def test_export_passes_schema_and_materials_without_results(kind, tmp_path, monkeypatch):
    script = (Path(__file__).resolve().parents[3]
              / ".codex/skills/caliboo-strength-run/scripts/jobs.py")
    spec = importlib.util.spec_from_file_location("strength_jobs_cli", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    materials = normalize_strength_materials({"sources": [source()]})
    job = dict(id=7, kind=kind, userId=123, result={"answer": "非公開"}, materials=materials)
    schema = StrengthAnalysisMaterials.model_json_schema()
    responses = {
        "/api/auth/login": {}, "/api/development/jobs/7": job,
        "/api/development/strength-materials/schema": schema,
    }

    class Opener:
        def open(self, request, timeout):
            assert timeout == 30
            path = module.urllib.parse.urlparse(request.full_url).path
            return io.BytesIO(json.dumps(responses[path]).encode())

    monkeypatch.setattr(module.urllib.request, "build_opener", lambda handler: Opener())
    output = tmp_path / "input.json"
    monkeypatch.setattr(sys, "argv", [str(script), "--demo", "export", "7", str(output)])
    module.main()
    packet = json.loads(output.read_text())
    assert packet == ({"inputSchema": schema, "materials": materials}
                      if kind == "strength" else job)
