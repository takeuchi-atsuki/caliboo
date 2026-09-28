"""独立評価手順の合成fixture。本番品質の評価ではない。"""

from concurrent.futures import ThreadPoolExecutor

import pytest

from caliboo_api.db import session_scope
from caliboo_api.extension_models import StrengthHoldoutCase as Case, StrengthHoldoutLabel as Label
from caliboo_api.models import Report, User
from caliboo_api.routers.holdout import match_codes, summary

BASE = "/api/development/holdout/cases"


@pytest.fixture()
def evaluation(admin_client, client, login_as):
    with session_scope() as session:
        session.query(User).filter_by(login_id="sora").update({"role": "admin"})
        report_id = session.query(Report).filter_by(status="submitted").first().id
        session.commit()
    second = login_as("sora")
    response = admin_client.post(BASE, json=dict(reportId=report_id, realAndUnseen=True))
    assert response.status_code == 201
    case = response.json()
    source = next(source for source in case["materials"]["sources"] if source["evidenceEligible"])
    result = dict(trace=dict(provider="codex_agent", model="fixture", promptVersion="test"),
                  candidates=[dict(skillCode="TEST", label="検証", confidence=75,
                                   evidence=[dict(materialId=source["id"], quote=source["text"])],
                                   growthAction="再現する")], notes="合成ケース")
    return admin_client, second, case, result


def label(codes=None):
    return dict(skillCodes=["TEST"] if codes is None else codes, comment="独立した判断",
                outputUnseen=True)


def fix_labels(first, second, case):
    path = f"{BASE}/{case['id']}/labels"
    assert first.post(path, json=label()).status_code == 200
    assert second.post(path, json=label(["TEST", "PROG"])).status_code == 200


def result_payload(case, result):
    return dict(materialsDigest=case["materialsDigest"], result=result)


def test_frozen_materials_unique_reports_attestations_and_authorization(evaluation, client):
    first, second, case, result = evaluation
    assert len(case["materialsDigest"]) == 64
    path = f"{BASE}/{case['id']}"
    assert client.get(BASE).status_code == client.get(path).status_code == 403
    assert client.post(BASE, json=dict(reportId=case["reportId"], realAndUnseen=True)
                       ).status_code == 403
    assert first.get(f"{BASE}/99999").status_code == 404
    assert first.post(BASE, json=dict(reportId=99999, realAndUnseen=True)).status_code == 404
    assert first.post(BASE, json=dict(reportId=case["reportId"], realAndUnseen=True)
                      ).status_code == 409
    for value in (False, 1, "true"):
        assert first.post(BASE, json=dict(reportId=case["reportId"], realAndUnseen=value)
                          ).status_code == 422
        assert first.post(path + "/labels", json={**label(), "outputUnseen": value}
                          ).status_code == 422
    with session_scope() as session:
        session.get(Report, case["reportId"]).keep = "後から編集"
        session.commit()
    assert first.get(path).json()["materials"] == case["materials"]
    expected = dict(id=case["id"], reportId=case["reportId"], status="labeling")
    assert first.get(BASE).json()["cases"] == [expected]


def test_two_independent_immutable_labels_before_validated_result(evaluation):
    first, second, case, result = evaluation
    path = f"{BASE}/{case['id']}"
    payload = result_payload(case, result)
    assert first.post(path + "/result", json=payload).status_code == 409
    assert first.post(path + "/labels", json=label()).status_code == 200
    assert first.post(path + "/labels", json=label([])).status_code == 409
    hidden = second.get(path).json()
    assert hidden["labels"] == [] and hidden["result"] is None and hidden["labelCount"] == 1
    assert first.post(path + "/result", json=payload).status_code == 409
    assert second.post(path + "/labels", json=label(["PROG", "TEST"])).status_code == 200
    assert second.post(path + "/labels", json=label()).status_code == 409
    assert first.post(path + "/result", json={**payload, "materialsDigest": "0" * 64}
                      ).status_code == 409
    result["candidates"][0]["evidence"][0]["quote"] = "存在しない原文"
    assert first.post(path + "/result", json=result_payload(case, result)).status_code == 422
    assert first.get(path).json()["result"] is None


def test_acceptance_requires_own_label_and_result_and_is_fixed(evaluation, login_as):
    first, second, case, result = evaluation
    path = f"{BASE}/{case['id']}"
    acceptance = dict(accepted=True, comment="根拠が妥当")
    assert first.post(path + "/acceptance", json=acceptance).status_code == 409
    fix_labels(first, second, case)
    assert first.post(path + "/result", json=result_payload(case, result)).status_code == 200
    assert first.post(path + "/result", json=result_payload(case, result)).status_code == 409
    assert first.post(path + "/labels", json=label()).status_code == 409
    with session_scope() as session:
        session.query(User).filter_by(login_id="haruka").update({"role": "admin"})
        session.commit()
    third = login_as("haruka")
    assert third.post(path + "/acceptance", json=acceptance).status_code == 409
    assert first.post(path + "/acceptance", json=acceptance).status_code == 200
    assert first.post(path + "/acceptance", json=acceptance).status_code == 409
    assert first.get("/api/development/evaluations").json()["evaluatedJobs"] == 0
    assert second.post(path + "/acceptance", json=dict(accepted=False, comment="改善が必要")
                       ).status_code == 200
    actual = first.get("/api/development/evaluations").json()
    assert actual["status"] == "insufficient_data" and actual["evaluatedJobs"] == 1
    assert actual["agreement"] == 1 and actual["acceptance"] == 0.5
    view = first.get(path).json()
    assert {item["match"] for item in view["labels"]} == {"exact", "partial"}
    assert all(item["labeledAt"] and item["acceptedAt"] for item in view["labels"])
    assert view["resultAt"] and view["resultBy"]


def test_empty_and_draft_materials_are_rejected(admin_client):
    with session_scope() as session:
        report = session.query(Report).first()
        report.status = "draft"
        report_id = report.id
        session.commit()
    payload = dict(reportId=report_id, realAndUnseen=True)
    assert admin_client.post(BASE, json=payload).status_code == 404
    with session_scope() as session:
        report = session.get(Report, report_id)
        report.status, report.keep, report.problem, report.try_, report.mood_comment = (
            "submitted", "", "", "", "")
        session.commit()
    assert admin_client.post(BASE, json=payload).status_code == 409


def test_concurrent_labels_do_not_duplicate_reviewer(evaluation):
    first, second, case, result = evaluation
    path = f"{BASE}/{case['id']}/labels"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda index: first.post(path, json=label()).status_code, range(2)))
    assert sorted(results) == [200, 409]
    assert second.get(f"{BASE}/{case['id']}").json()["labelCount"] == 1


def test_holdout_thresholds_and_nonmatching_codes(user_ids):
    assert match_codes([], {"candidates": []}) == "exact"
    assert match_codes(["PROG"], {"candidates": [{"skillCode": "TEST"}]}) == "none"
    with session_scope() as session:
        for index in range(20):
            report = Report(user_id=user_ids["yuki"], date=f"2026-08-{index + 1:02d}",
                            keep="合成日報", problem="", try_="", status="submitted", saved_at="1")
            session.add(report)
            session.flush()
            case = Case(report_id=report.id, materials={}, digest="fixture", created_at="1",
                        created_by=user_ids["sensei"], status="result_ready", result_at="3",
                        result={"trace": {"provider": "codex_agent", "model": "fixture",
                                          "promptVersion": "v1"},
                                "candidates": [{"skillCode": "TEST"}]})
            session.add(case)
            session.flush()
            for reviewer in (user_ids["sensei"], user_ids["sora"]):
                session.add(Label(case_id=case.id, reviewer_id=reviewer, skill_codes=["TEST"],
                                  comment="合成fixture", labeled_at="2", accepted=index < 16,
                                  acceptance_comment="合成fixture", accepted_at="4"))
        session.commit()
        result = summary(session)
        assert result["status"] == "passed" and result["evaluatedJobs"] == 20
        assert result["acceptance"] == 0.8
        session.query(Label).filter_by(case_id=case.id).update({"skill_codes": []})
        session.query(Label).filter(Label.case_id != case.id).update({"accepted": False})
        session.commit()
        assert summary(session)["status"] == "failed"

        new_trace = dict(provider="codex_agent", model="new-model", promptVersion="v2")
        case.result = {**case.result, "trace": new_trace}
        session.commit()
        changed = summary(session)
        assert changed["status"] == "insufficient_data" and changed["evaluatedJobs"] == 1
        assert changed["trace"]["model"] == "new-model"
