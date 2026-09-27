"""AIの課題案API(`/api/assignment-proposals`)の仕様テスト。"""

import caliboo_api.db as db
from caliboo_api.models import Report


def _user_id(client) -> int:
    return client.get("/api/auth/me").json()["id"]


def _create_proposal(admin_client, user_id: int) -> dict:
    response = admin_client.post("/api/assignment-proposals", json={"userId": user_id})
    assert response.status_code == 201
    return response.json()


def _insert_report(user_id: int, date: str, problem: str = "特に無い。", try_: str = "特に無い。") -> None:
    with db.session_scope() as session:
        session.add(
            Report(
                user_id=user_id,
                date=date,
                keep="特に無い。",
                problem=problem,
                try_=try_,
                mood=[],
                mood_comment="特に無い。",
                status="submitted",
                saved_at=f"{date}T18:00:00+00:00",
            )
        )
        session.commit()


# --- ロール(講師のみ) ---


def test_member_cannot_list_proposals_returns_403(client):
    response = client.get("/api/assignment-proposals")

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


def test_member_cannot_list_proposals_by_assignment_id_returns_403(client):
    """観点: `?assignmentId=`付きの一覧も、新入社員が呼ぶと403になる(認可はクエリの
    有無に関わらず先に働く)。"""
    response = client.get("/api/assignment-proposals?assignmentId=1")

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


def test_member_cannot_create_proposal_returns_403(client, other_member_client):
    sora_id = _user_id(other_member_client)

    response = client.post("/api/assignment-proposals", json={"userId": sora_id})

    assert response.status_code == 403


def test_member_cannot_approve_or_reject_returns_403(client):
    response = client.post(
        "/api/assignment-proposals/1/approve",
        json={"title": "t", "body": "b", "messageForMember": ""},
    )
    assert response.status_code == 403

    response = client.post("/api/assignment-proposals/1/reject", json={})
    assert response.status_code == 403


# --- 生成(POST) ---


def test_create_proposal_returns_201_with_pending_status(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)

    created = _create_proposal(admin_client, sora_id)

    assert created["status"] == "pending"
    assert created["target"] == {"id": sora_id, "displayName": "ソラ"}
    assert created["assignmentId"] is None
    assert created["decidedAt"] is None
    assert created["edited"] is False
    assert created["generator"] == "rule_based_v1"
    assert isinstance(created["materials"], list)
    assert created["progress"]["notSubmittedCount"] >= 0


def test_create_proposal_when_pending_exists_returns_200_same_proposal(
    admin_client, other_member_client
):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = admin_client.post("/api/assignment-proposals", json={"userId": sora_id})

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_create_proposal_for_admin_user_returns_404(admin_client):
    admin_id = _user_id(admin_client)

    response = admin_client.post("/api/assignment-proposals", json={"userId": admin_id})

    assert response.status_code == 404


def test_create_proposal_for_unknown_user_returns_404(admin_client):
    response = admin_client.post("/api/assignment-proposals", json={"userId": 999999})

    assert response.status_code == 404


# --- 詳細(GET) ---


def test_get_proposal_detail_returns_full_fields(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = admin_client.get(f"/api/assignment-proposals/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert "rationale" in body
    assert "aim" in body
    assert "estimateMinutes" in body
    assert body["rejectReason"] is None
    assert body["decidedBy"] is None


def test_get_proposal_detail_missing_returns_404(admin_client):
    response = admin_client.get("/api/assignment-proposals/999999")

    assert response.status_code == 404


def test_member_cannot_get_proposal_detail_returns_403(admin_client, other_member_client, client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = client.get(f"/api/assignment-proposals/{created['id']}")

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


# --- 一覧(GET) ---


def test_list_proposals_default_status_is_pending(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = admin_client.get("/api/assignment-proposals")

    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == created["id"] for item in body["proposals"])
    assert all(item["status"] == "pending" for item in body["proposals"])


def test_list_proposals_invalid_status_returns_422(admin_client):
    response = admin_client.get("/api/assignment-proposals?status=bogus")

    assert response.status_code == 422


def test_list_proposals_members_include_has_pending_flag(
    admin_client, other_member_client, client, third_member_client
):
    """観点: pendingCountは確認待ちの件数、membersは表示名順で講師を含まず、
    確認待ちが無い新入社員はhasPending=falseになる。"""
    sora_id = _user_id(other_member_client)
    admin_id = _user_id(admin_client)
    _create_proposal(admin_client, sora_id)

    response = admin_client.get("/api/assignment-proposals")
    body = response.json()

    members = body["members"]
    sora_member = next(item for item in members if item["id"] == sora_id)
    assert sora_member["hasPending"] is True
    yuki_member = next(item for item in members if item["id"] == _user_id(client))
    assert yuki_member["hasPending"] is False
    assert all(member["id"] != admin_id for member in members)
    assert [member["displayName"] for member in members] == sorted(
        member["displayName"] for member in members
    )
    assert {"ソラ", "ハルカ", "ユウキ"} <= {member["displayName"] for member in members}
    assert body["pendingCount"] == 1

    # third_member_clientはメンバー一覧に日報シードを持つハルカが含まれることの確認用。
    assert _user_id(third_member_client) in {member["id"] for member in members}


def test_list_proposals_are_ordered_by_created_at_desc(
    admin_client, other_member_client, client, third_member_client
):
    sora_id = _user_id(other_member_client)
    yuki_id = _user_id(client)
    haruka_id = _user_id(third_member_client)

    first = _create_proposal(admin_client, sora_id)
    second = _create_proposal(admin_client, yuki_id)
    third = _create_proposal(admin_client, haruka_id)

    proposals = admin_client.get("/api/assignment-proposals").json()["proposals"]

    assert [item["id"] for item in proposals] == [third["id"], second["id"], first["id"]]


def test_list_proposals_by_status_approved_is_empty_before_approval(
    admin_client, other_member_client
):
    sora_id = _user_id(other_member_client)
    _create_proposal(admin_client, sora_id)

    response = admin_client.get("/api/assignment-proposals?status=approved")

    assert response.status_code == 200
    assert response.json()["proposals"] == []


def test_list_proposals_filters_by_each_status_returns_only_matching(
    admin_client, other_member_client, client, third_member_client
):
    """観点: 課題案一覧は状態(確認待ち/配信済み/見送り)で絞り込める。"""
    sora_id = _user_id(other_member_client)
    yuki_id = _user_id(client)
    haruka_id = _user_id(third_member_client)

    pending = _create_proposal(admin_client, sora_id)
    approved_source = _create_proposal(admin_client, yuki_id)
    approved = admin_client.post(
        f"/api/assignment-proposals/{approved_source['id']}/approve",
        json={"title": "タイトル", "body": "本文", "messageForMember": ""},
    ).json()
    rejected_source = _create_proposal(admin_client, haruka_id)
    rejected = admin_client.post(
        f"/api/assignment-proposals/{rejected_source['id']}/reject", json={}
    ).json()

    def _ids_for_status(status: str) -> set[int]:
        proposals = admin_client.get(f"/api/assignment-proposals?status={status}").json()[
            "proposals"
        ]
        return {item["id"] for item in proposals}

    assert _ids_for_status("pending") == {pending["id"]}
    assert _ids_for_status("approved") == {approved["id"]}
    assert _ids_for_status("rejected") == {rejected["id"]}


# --- 配信(approve) ---


def test_approve_creates_assignment_and_marks_approved(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "編集後タイトル", "body": "編集後の課題文", "messageForMember": "頑張って"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["assignmentId"] is not None
    assert body["edited"] is True
    assert body["decidedBy"]["displayName"] == "佐藤先生"

    sora_detail = other_member_client.get(f"/api/assignments/{body['assignmentId']}").json()
    assert sora_detail["title"] == "編集後タイトル"
    assert sora_detail["body"] == "編集後の課題文"
    assert sora_detail["messageForMember"] == "頑張って"
    assert sora_detail["target"] == {"id": sora_id, "displayName": "ソラ"}


def test_approve_does_not_change_proposal_record_title_body_and_message(
    admin_client, other_member_client
):
    """観点: 配信後も課題案自体のtitle/body/messageForMemberは生成時のまま変わらない
    (配信内容の変更は`assignments`/`assignment_recipients`側にのみ反映される)。"""
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "編集後タイトル", "body": "編集後の課題文", "messageForMember": "頑張って"},
    )

    detail = admin_client.get(f"/api/assignment-proposals/{created['id']}").json()
    assert detail["title"] == created["title"]
    assert detail["body"] == created["body"]
    assert detail["messageForMember"] == created["messageForMember"]


def test_approve_with_only_message_for_member_change_has_edited_true(
    admin_client, other_member_client
):
    """観点: messageForMemberのみの変更でもedited=trueになる。"""
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={
            "title": created["title"],
            "body": created["body"],
            "messageForMember": "生成時とは異なるひとこと",
        },
    )

    assert response.status_code == 200
    assert response.json()["edited"] is True


def test_approve_blank_message_for_member_normalizes_to_null(admin_client, other_member_client):
    """観点: messageForMemberが空文字/空白のみの場合はnullに正規化される。"""
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    approved = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": created["title"], "body": created["body"], "messageForMember": "   "},
    ).json()

    sora_detail = other_member_client.get(f"/api/assignments/{approved['assignmentId']}").json()
    assert sora_detail["messageForMember"] is None


def test_approve_without_edits_has_edited_false(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={
            "title": created["title"],
            "body": created["body"],
            "messageForMember": created["messageForMember"] or "",
        },
    )

    assert response.status_code == 200
    assert response.json()["edited"] is False


def test_approve_hides_assignment_from_other_members(admin_client, other_member_client, client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)
    approved = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "個人宛て課題", "body": "本文", "messageForMember": ""},
    ).json()
    assignment_id = approved["assignmentId"]

    yuki_detail_response = client.get(f"/api/assignments/{assignment_id}")
    assert yuki_detail_response.status_code == 404

    yuki_list = client.get("/api/assignments").json()["assignments"]
    assert all(item["id"] != assignment_id for item in yuki_list)

    yuki_submit_response = client.post(
        f"/api/assignments/{assignment_id}/submission", json={"answerText": "回答"}
    )
    assert yuki_submit_response.status_code == 404


def test_approve_blank_title_returns_422(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": " ", "body": "本文", "messageForMember": ""},
    )

    assert response.status_code == 422


def test_approve_blank_body_returns_422(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "タイトル", "body": "", "messageForMember": ""},
    )

    assert response.status_code == 422


def test_approve_already_approved_returns_409(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)
    admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "タイトル", "body": "本文", "messageForMember": ""},
    )

    response = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "タイトル2", "body": "本文2", "messageForMember": ""},
    )

    assert response.status_code == 409


def test_approve_missing_proposal_returns_404(admin_client):
    response = admin_client.post(
        "/api/assignment-proposals/999999/approve",
        json={"title": "タイトル", "body": "本文", "messageForMember": ""},
    )

    assert response.status_code == 404


# --- 見送り(reject) ---


def test_reject_marks_rejected_with_reason(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/reject", json={"reason": "今は負担が大きい"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["assignmentId"] is None
    assert body["rejectReason"] == "今は負担が大きい"
    assert body["decidedBy"]["displayName"] == "佐藤先生"


def test_reject_without_reason_is_allowed(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)

    response = admin_client.post(f"/api/assignment-proposals/{created['id']}/reject", json={})

    assert response.status_code == 200
    assert response.json()["rejectReason"] is None


def test_reject_already_rejected_returns_409(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)
    admin_client.post(f"/api/assignment-proposals/{created['id']}/reject", json={})

    response = admin_client.post(f"/api/assignment-proposals/{created['id']}/reject", json={})

    assert response.status_code == 409


def test_reject_missing_proposal_returns_404(admin_client):
    response = admin_client.post("/api/assignment-proposals/999999/reject", json={})

    assert response.status_code == 404


def test_reject_does_not_change_assignment_count(admin_client, other_member_client):
    """観点: 見送ると課題案は「見送り」になり課題は作成されない(課題件数が変わらない)。"""
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)
    before_count = len(admin_client.get("/api/assignments").json()["assignments"])

    response = admin_client.post(f"/api/assignment-proposals/{created['id']}/reject", json={})

    assert response.status_code == 200
    after_count = len(admin_client.get("/api/assignments").json()["assignments"])
    assert after_count == before_count


def test_reject_after_approve_returns_409(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)
    admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "タイトル", "body": "本文", "messageForMember": ""},
    )

    response = admin_client.post(f"/api/assignment-proposals/{created['id']}/reject", json={})

    assert response.status_code == 409


def test_approve_after_reject_returns_409(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)
    admin_client.post(f"/api/assignment-proposals/{created['id']}/reject", json={})

    response = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "タイトル", "body": "本文", "messageForMember": ""},
    )

    assert response.status_code == 409


# --- 材料・進捗・除外テーマ(生成規則の一部をAPI経由で確認) ---


def test_materials_include_report_quote_with_date_and_progress_values(
    admin_client, other_member_client
):
    """観点: 分析した材料(日報からの引用と日付)が付き、生成時点の状況(提出数等)が
    具体的に検証できる。"""
    sora_id = _user_id(other_member_client)
    _insert_report(sora_id, "2026-09-10", problem="SQLのJOINで悩んだ。")

    created = _create_proposal(admin_client, sora_id)

    assert created["title"] == "テーブル結合(JOIN)を復習しよう"
    report_materials = [m for m in created["materials"] if m["kind"] == "report"]
    assert {
        "kind": "report",
        "date": "2026-09-10",
        "quote": "SQLのJOINで悩んだ。",
        "sourceLabel": "日報 Problem",
    } in report_materials
    assert created["progress"] == {
        "submittedCount": 0,
        "reviewedCount": 0,
        "notSubmittedCount": 3,
        "recentMoods": [],
    }


def test_regenerate_after_approval_excludes_delivered_theme_via_api(
    admin_client, other_member_client
):
    """観点: その新入社員に配信済みのテーマは次の課題案で選ばれない
    (除外後に選ばれるテーマを肯定形で固定する)。"""
    sora_id = _user_id(other_member_client)
    _insert_report(sora_id, "2026-09-01", problem="Gitのブランチ運用で困った。")

    first = _create_proposal(admin_client, sora_id)
    assert first["title"] == "Gitのブランチ運用を整理しよう"
    admin_client.post(
        f"/api/assignment-proposals/{first['id']}/approve",
        json={"title": first["title"], "body": first["body"], "messageForMember": ""},
    )

    second = _create_proposal(admin_client, sora_id)

    assert second["id"] != first["id"]
    assert second["title"] == "今週の振り返りをまとめよう"


# --- assignmentIdによる絞り込み ---


def test_list_proposals_by_assignment_id_returns_originating_proposal(
    admin_client, other_member_client
):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)
    approved = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "タイトル", "body": "本文", "messageForMember": ""},
    ).json()

    response = admin_client.get(
        f"/api/assignment-proposals?assignmentId={approved['assignmentId']}&status=rejected"
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["proposals"]] == [created["id"]]


# --- 個人宛て提出一覧・フィードバックの可視性 ---


def test_admin_submission_list_shows_only_target_member(admin_client, other_member_client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)
    approved = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "タイトル", "body": "本文", "messageForMember": ""},
    ).json()

    submissions = admin_client.get(
        f"/api/assignments/{approved['assignmentId']}/submissions"
    ).json()["submissions"]

    assert [item["user"]["displayName"] for item in submissions] == ["ソラ"]


def test_feedback_to_non_target_member_returns_404(admin_client, other_member_client, client):
    sora_id = _user_id(other_member_client)
    created = _create_proposal(admin_client, sora_id)
    approved = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={"title": "タイトル", "body": "本文", "messageForMember": ""},
    ).json()
    other_member_client.post(
        f"/api/assignments/{approved['assignmentId']}/submission", json={"answerText": "回答"}
    )
    yuki_id = _user_id(client)

    response = admin_client.post(
        f"/api/assignments/{approved['assignmentId']}/submissions/{yuki_id}/feedback",
        json={"comment": "コメント"},
    )

    assert response.status_code == 404
