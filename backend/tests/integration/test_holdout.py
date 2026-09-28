"""独立ラベル→引用検証→受容性の手順と本人への非配信。合成データのみ。"""

from concurrent.futures import ThreadPoolExecutor

from caliboo_api.db import bootstrap_db, session_scope
from caliboo_api.extension_models import StrengthCandidate
from caliboo_api.models import Report, User

BASE = "/api/development/holdout/cases"


def test_blind_holdout_flow_persists_without_publishing(client, admin_client, login_as):
    user_id = client.get("/api/auth/me").json()["id"]
    client.post("/api/report", json=dict(date="2026-09-29", keep="条件を比較して境界を確認した。",
                problem="説明", **{"try": "共有"}, status="submitted"))
    with session_scope() as session:
        report_id = session.query(Report).filter_by(user_id=user_id).order_by(
            Report.id.desc()).first().id
        session.query(User).filter_by(login_id="sora").update({"role": "admin"})
        candidate_count = session.query(StrengthCandidate).count()
        session.commit()
    second = login_as("sora")
    case = admin_client.post(BASE, json=dict(reportId=report_id, realAndUnseen=True)).json()
    path = f"{BASE}/{case['id']}"
    source = case["materials"]["sources"][0]
    for reviewer in (admin_client, second):
        assert reviewer.get(path).json()["labels"] == []
        assert reviewer.post(path + "/labels", json=dict(
            skillCodes=["TEST"], comment="本人の行動から独立判断", outputUnseen=True)).status_code == 200
    payload = dict(materialsDigest=case["materialsDigest"], result=dict(
        trace=dict(provider="codex_agent", model="synthetic", promptVersion="test"),
        candidates=[dict(skillCode="TEST", label="検証", confidence=70, growthAction="共有する",
                         evidence=[dict(materialId=source["id"], quote=source["text"])])],
        notes="合成テスト"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda index: admin_client.post(
            path + "/result", json=payload).status_code, range(2)))
    assert sorted(statuses) == [200, 409]
    bootstrap_db()
    for reviewer in (admin_client, second):
        assert reviewer.get(path).json()["result"] == payload["result"]
        assert reviewer.post(path + "/acceptance", json=dict(
            accepted=True, comment="講師として受容できる")).status_code == 200
    summary = admin_client.get("/api/development/evaluations").json()
    assert summary["evaluatedJobs"] == 1 and summary["status"] == "insufficient_data"
    with session_scope() as session:
        assert session.query(StrengthCandidate).count() == candidate_count
    for endpoint in (BASE, path):
        assert client.get(endpoint).status_code == 403
    for endpoint, body in ((BASE, dict(reportId=report_id, realAndUnseen=True)),
                           (path + "/labels", dict(skillCodes=[], comment="理由", outputUnseen=True)),
                           (path + "/result", payload),
                           (path + "/acceptance", dict(accepted=True, comment="理由"))):
        assert client.post(endpoint, json=body).status_code == 403
