"""部署別OJT設定: OJT-F1〜F5のAPI契約と既存DBの移行。"""

import pytest

import caliboo_api.db as db
from caliboo_api.extension_models import OjtConfiguration
from caliboo_api.data.ojt_configuration import configuration_view
from caliboo_api.models import DepartmentMessage, KnowledgeItem


def settings(**changes):
    return dict(name="研究課", icon="ph ph-code", color="#d6ebff",
                welcomeMessage="研究課へようこそ。", quickAsks=["実験の記録方法は？", "相談先は？"],
                replyGuidance="確認できない点は担当講師に相談してください。",
                knowledge=[dict(title="実験記録", description="条件と結果を残す")], **changes)


def test_configuration_create_update_and_empty_lists(admin_client, client):
    created = admin_client.post("/api/ojt/departments", json=settings(id="research"))
    assert created.status_code == 201
    path = "/api/ojt/departments/research/configuration"
    config = created.json()
    assert config["revision"] == 1
    assert admin_client.get(path).json() == config
    departments = client.get("/api/ojt/departments").json()["departments"]
    assert departments[-1]["quickAsks"] == config["quickAsks"]
    assert departments[-1]["knowledgeCount"] == 1
    reply = client.post("/api/ojt/chat", json=dict(deptId="research", text="手順は？"))
    assert reply.json()["text"].endswith(config["replyGuidance"])

    changes = {key: value for key, value in config.items() if key != "id"}
    changes.update(quickAsks=[], knowledge=[], replyGuidance="", name="研究室")
    updated = admin_client.post(path, json=changes)
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2
    assert updated.json()["quickAsks"] == []
    assert client.get("/api/ojt/departments/research/knowledge").json()["items"] == []
    departments = client.get("/api/ojt/departments").json()["departments"]
    assert departments[-1]["knowledgeCount"] == 0
    assert departments[-1]["name"] == "研究室"


def test_configuration_missing_and_duplicate(admin_client):
    assert admin_client.get("/api/ojt/departments/missing/configuration").status_code == 404
    assert admin_client.post("/api/ojt/departments/missing/configuration",
                             json=settings(revision=1)).status_code == 404
    before = admin_client.get("/api/ojt/departments/dev/configuration").json()
    assert admin_client.post("/api/ojt/departments", json=settings(id="dev")).status_code == 409
    assert admin_client.get("/api/ojt/departments/dev/configuration").json() == before


@pytest.mark.parametrize("field,value", [
    ("id", "../path"), ("id", "A"), ("id", "a" * 41), ("id", ""),
    ("name", " \n "), ("name", "a" * 101), ("icon", "ph invalid"), ("color", "red"),
    ("welcomeMessage", " \n"), ("welcomeMessage", "a" * 4001),
    ("replyGuidance", "a" * 4001), ("quickAsks", ["x"] * 9),
    ("quickAsks", ["  "]), ("quickAsks", ["a" * 201]),
    ("knowledge", [dict(title="x", description="y")] * 101),
    ("knowledge", [dict(title=" ", description="y")]),
    ("knowledge", [dict(title="x", description=" ")]),
    ("knowledge", [dict(title="a" * 201, description="y")]),
    ("knowledge", [dict(title="x", description="a" * 4001)]),
    ("unknownSetting", True),
])
def test_configuration_rejects_invalid_create(admin_client, field, value):
    payload = {**settings(id="research"), field: value}
    assert admin_client.post("/api/ojt/departments", json=payload).status_code == 422
    assert admin_client.get("/api/ojt/departments/research/configuration").status_code == 404


@pytest.mark.parametrize("revision", [0, -1, "1", True, 1.5, None])
def test_revision_requires_positive_integer(admin_client, revision):
    assert admin_client.post("/api/ojt/departments/dev/configuration",
                             json=settings(revision=revision)).status_code == 422


def test_configuration_limits_and_whitespace_normalization(admin_client):
    payload = settings(id="a" * 40)
    payload.update(name="  研究室  ", welcomeMessage="  案内  ", replyGuidance="x" * 4000,
                   quickAsks=["q" * 200] * 8,
                   knowledge=[dict(title="k" * 200, description="d" * 4000)] * 100)
    response = admin_client.post("/api/ojt/departments", json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == "研究室"
    assert response.json()["welcomeMessage"] == "案内"


def test_configuration_management_requires_admin(client, anonymous_client):
    for caller, status in [(client, 403), (anonymous_client, 401)]:
        assert caller.get("/api/ojt/departments/dev/configuration").status_code == status
        assert caller.post("/api/ojt/departments",
                           json=settings(id="research")).status_code == status
        assert caller.post("/api/ojt/departments/dev/configuration",
                           json=settings(revision=1)).status_code == status


def test_conflict_is_atomic_and_correct_revision_can_retry(admin_client, client):
    path = "/api/ojt/departments/dev/configuration"
    original = admin_client.get(path).json()
    first = settings(revision=original["revision"])
    saved = admin_client.post(path, json=first).json()
    rejected = {**first, "name": "上書き禁止", "knowledge": [], "welcomeMessage": "上書き"}
    assert admin_client.post(path, json=rejected).status_code == 409
    assert admin_client.get(path).json() == saved
    assert client.get("/api/ojt/departments/dev/messages").json()["messages"][0]["text"] == (
        first["welcomeMessage"])
    assert len(client.get("/api/ojt/departments/dev/knowledge").json()["items"]) == 1
    retry = admin_client.post(path, json={**rejected, "revision": saved["revision"]})
    assert retry.status_code == 200


def test_existing_database_migration_preserves_content_and_saved_configuration(bootstrapped_db):
    with db.session_scope() as session:
        session.query(DepartmentMessage).filter_by(department_id="dev").first().text = "既存案内"
        item = session.query(KnowledgeItem).filter_by(department_id="dev").first()
        item.title = "  既存資料  "
        item.description = ""
        session.commit()
    # 追加テーブルのない旧DBからの起動を再現する（一時DBのみ）。
    OjtConfiguration.__table__.drop(db._engine)
    db.bootstrap_db()
    with db.session_scope() as session:
        assert session.query(OjtConfiguration).count() == 6
        message = session.query(DepartmentMessage).filter_by(department_id="dev").first()
        assert message.text == "既存案内"
        content = configuration_view(session, "dev").knowledge[0]
        assert content.title == "  既存資料  "
        assert content.description == ""
        config = session.get(OjtConfiguration, "dev")
        config.quick_asks = []
        config.reply_guidance = "カスタマイズ済み"
        config.revision = 8
        session.commit()
    db.init_engine(bootstrapped_db)
    db.bootstrap_db()
    with db.session_scope() as session:
        config = session.get(OjtConfiguration, "dev")
        assert config.quick_asks == []
        assert config.reply_guidance == "カスタマイズ済み"
        assert config.revision == 8
