"""承認済み観点: 強み解釈の保存、本人表示、旧形式と種類別置換。"""

from caliboo_api.db import session_scope
from caliboo_api.extension_models import StrengthCandidate, StrengthInterpretation
from caliboo_api.models import Report, User

TRACE = dict(provider="codex_agent", model="test", promptVersion="profile-test")


def submit_report(client, date, keep):
    response = client.post("/api/report", json=dict(
        date=date, keep=keep, problem="説明を考える", **{"try": "明日共有する"},
        moodComment="嬉しい", status="submitted"))
    assert response.status_code == 200, response.text


def job_and_sources(admin_client, user_id):
    job = admin_client.post(f"/api/development/strengths/{user_id}/request").json()
    assert job["id"]
    materials = admin_client.get(f"/api/development/jobs/{job['id']}").json()["materials"]
    return job["id"], {row["id"]: row for row in materials["sources"]}


def candidate(kind, sources, source_ids):
    return dict(kind=kind, skillCode="TEST", label="結果を確かめる力" if kind == "ability"
                else "慎重に確かめる傾向", summary="複数の作業で結果を照合した。",
                scopeNote="今回の提出と日報に限る。", confidence=80,
                evidence=[dict(materialId=source_id, quote=sources[source_id]["text"])
                          for source_id in source_ids], growthAction="次の結果も照合する")


def import_result(admin_client, job_id, candidates):
    return admin_client.post(f"/api/development/jobs/{job_id}/strength-result", json=dict(
        trace=TRACE, candidates=candidates, notes="提出された原文から解釈した。"))


def decide(admin_client, row, **overrides):
    body = dict(status="approved", kind=row["kind"], label=row["label"],
                growthAction=row["growthAction"])
    body.update(overrides)
    return admin_client.post(f"/api/development/strengths/{row['id']}/decision", json=body)


def test_profile_approval_edit_and_kind_specific_replacement(client, admin_client):
    user_id = client.get("/api/auth/me").json()["id"]
    submit_report(client, "2026-09-27", "境界値を確認した。")
    submit_report(client, "2026-09-28", "異常系の結果を照合した。")
    job_id, sources = job_and_sources(admin_client, user_id)
    keeps = [source_id for source_id, row in sources.items() if row["field"] == "keep"
             and row["kind"] == "report"]
    assert len(keeps) >= 2
    response = import_result(admin_client, job_id, [
        candidate("ability", sources, keeps[:1]), candidate("work_style", sources, keeps[:2])])
    assert response.status_code == 200, response.text
    admin_path = f"/api/development/strengths?userId={user_id}"
    pending = admin_client.get(admin_path).json()["candidates"]
    assert {(row["kind"], row["skillCode"]) for row in pending[:2]} == {
        ("ability", "TEST"), ("work_style", "TEST")}
    assert client.get("/api/development/strengths").json()["candidates"] == []
    assert client.get("/api/home/summary").json()["strengths"] == []
    by_kind = {row["kind"]: row for row in pending[:2]}
    style = by_kind["work_style"]
    assert decide(admin_client, style, summary="  ").status_code == 422
    assert decide(admin_client, style, kind="ability").status_code == 422
    assert decide(admin_client, style, summary="2件の記録で確認した。",
                  scopeNote="2件の記録のみ。", label="記録を確かめる傾向").status_code == 200
    assert decide(admin_client, by_kind["ability"]).status_code == 200
    member = client.get("/api/development/strengths").json()["candidates"]
    assert {row["kind"] for row in member} == {"ability", "work_style"}
    approved_style = next(row for row in member if row["kind"] == "work_style")
    assert (approved_style["label"], approved_style["summary"], approved_style["scopeNote"]) == (
        "記録を確かめる傾向", "2件の記録で確認した。", "2件の記録のみ。")
    home = client.get("/api/home/summary").json()["strengths"]
    assert {(row["kind"], row["summary"], row["scopeNote"]) for row in home} == {
        ("ability", "複数の作業で結果を照合した。", "今回の提出と日報に限る。"),
        ("work_style", "2件の記録で確認した。", "2件の記録のみ。"),
    }

    submit_report(client, "2026-09-29", "もう一度異常系を確認した。")
    next_job, next_sources = job_and_sources(admin_client, user_id)
    next_keep = next(source_id for source_id, row in next_sources.items()
                     if row["text"] == "もう一度異常系を確認した。")
    assert import_result(admin_client, next_job, [
        candidate("ability", next_sources, [next_keep])]).status_code == 200
    newest = admin_client.get(admin_path).json()["candidates"][0]
    assert client.get("/api/development/strengths").json()["candidates"][-1]["kind"] == "ability"
    assert decide(admin_client, newest).status_code == 200
    current = client.get("/api/development/strengths").json()["candidates"]
    assert {(row["kind"], row["status"]) for row in current} == {
        ("ability", "approved"), ("work_style", "approved")}
    assert next(row for row in admin_client.get(admin_path).json()["candidates"]
                if row["id"] == by_kind["ability"]["id"])["status"] == "superseded"


def test_legacy_candidate_and_old_same_kind_guard(client, admin_client):
    user_id = client.get("/api/auth/me").json()["id"]
    submit_report(client, "2026-09-27", "古い記録で確認した。")
    old_job, old_sources = job_and_sources(admin_client, user_id)
    source_id = next(source_id for source_id, row in old_sources.items()
                     if row["text"] == "古い記録で確認した。")
    assert import_result(admin_client, old_job, [
        candidate("ability", old_sources, [source_id])]).status_code == 200
    with session_scope() as session:
        old = session.query(StrengthCandidate).filter_by(job_id=old_job).one()
        session.query(StrengthInterpretation).filter_by(candidate_id=old.id).delete()
        legacy_approved = StrengthCandidate(
            user_id=user_id, job_id=old_job, label="旧承認の確認力", skill_code="TEST",
            confidence=70, evidence=old.evidence, growth_action="共有する", status="approved")
        session.add(legacy_approved)
        session.commit()
        old_id, approved_id = old.id, legacy_approved.id
    legacy = admin_client.get(f"/api/development/strengths?userId={user_id}").json()[
        "candidates"][0]
    assert legacy["kind"] == "ability" and legacy["summary"] == legacy["scopeNote"] == ""
    submit_report(client, "2026-09-28", "新しい記録で確認した。")
    new_job, new_sources = job_and_sources(admin_client, user_id)
    new_id = next(source_id for source_id, row in new_sources.items()
                  if row["text"] == "新しい記録で確認した。")
    assert import_result(admin_client, new_job, [
        candidate("ability", new_sources, [new_id])]).status_code == 200
    new_row = admin_client.get(f"/api/development/strengths?userId={user_id}").json()[
        "candidates"][0]
    assert decide(admin_client, new_row).status_code == 200
    assert admin_client.post(f"/api/development/strengths/{old_id}/decision", json=dict(
        status="approved", label="古い確認", growthAction="共有する")).status_code == 409
    with session_scope() as session:
        assert session.get(StrengthCandidate, old_id).status == "pending"
        assert session.get(StrengthCandidate, approved_id).status == "superseded"
        assert session.query(StrengthInterpretation).filter_by(candidate_id=old_id).count() == 0


def test_new_style_approval_does_not_block_older_ability(client, admin_client):
    user_id = client.get("/api/auth/me").json()["id"]
    submit_report(client, "2026-09-27", "最初の結果を確かめた。")
    old_job, old_sources = job_and_sources(admin_client, user_id)
    first = next(source_id for source_id, row in old_sources.items()
                 if row["text"] == "最初の結果を確かめた。")
    assert import_result(admin_client, old_job, [
        candidate("ability", old_sources, [first])]).status_code == 200
    old_ability = admin_client.get(f"/api/development/strengths?userId={user_id}").json()[
        "candidates"][0]

    submit_report(client, "2026-09-28", "次の結果も確かめた。")
    new_job, new_sources = job_and_sources(admin_client, user_id)
    second = next(source_id for source_id, row in new_sources.items()
                  if row["text"] == "次の結果も確かめた。")
    assert import_result(admin_client, new_job, [
        candidate("work_style", new_sources, [first, second])]).status_code == 200
    new_style = admin_client.get(f"/api/development/strengths?userId={user_id}").json()[
        "candidates"][0]
    assert decide(admin_client, new_style).status_code == 200
    assert decide(admin_client, old_ability).status_code == 200
    approved = client.get("/api/development/strengths").json()["candidates"]
    assert {(row["kind"], row["status"]) for row in approved} == {
        ("ability", "approved"), ("work_style", "approved")}


def test_holdout_keeps_explicit_interpretation_without_publishing(client, admin_client, login_as):
    user_id = client.get("/api/auth/me").json()["id"]
    submit_report(client, "2026-09-29", "結果を照合した。")
    with session_scope() as session:
        report_id = session.query(Report).filter_by(user_id=user_id).order_by(
            Report.id.desc()).first().id
        session.query(User).filter_by(login_id="sora").update({"role": "admin"})
        session.commit()
    second = login_as("sora")
    base = "/api/development/holdout/cases"
    case = admin_client.post(base, json=dict(reportId=report_id, realAndUnseen=True)).json()
    path = f"{base}/{case['id']}"
    source = next(row for row in case["materials"]["sources"] if row["field"] == "keep")
    for reviewer in (admin_client, second):
        assert reviewer.post(path + "/labels", json=dict(
            skillCodes=["TEST"], comment="記録を確認", outputUnseen=True)).status_code == 200
    ability = candidate("ability", {source["id"]: source}, [source["id"]])
    payload = dict(materialsDigest=case["materialsDigest"], result=dict(
        trace=TRACE, candidates=[{**ability, "kind": "work_style"}], notes="1件だけ"))
    assert admin_client.post(path + "/result", json=payload).status_code == 422
    payload["result"]["candidates"] = [ability]
    assert admin_client.post(path + "/result", json=payload).status_code == 200
    assert admin_client.get(path).json()["result"] == payload["result"]
    assert client.get("/api/development/strengths").json()["candidates"] == []
