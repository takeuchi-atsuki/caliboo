def _create_assignment(admin_client, title="新しい課題", body="課題の説明文"):
    response = admin_client.post("/api/assignments", json={"title": title, "body": body})
    assert response.status_code == 200
    return response.json()


# --- 一覧・詳細(ロールによらず「本人の提出」を表す) ---


def test_initial_assignment_list_has_seeded_three_states(client):
    """`client`(yuki)は既存シード(reviewed/submitted/not_submitted)を引き継ぐ。"""
    response = client.get("/api/assignments")

    assert response.status_code == 200
    items = response.json()["assignments"]
    assert len(items) == 3
    assert [item["status"] for item in items] == ["not_submitted", "submitted", "reviewed"]


def test_seeded_assignments_are_not_submitted_for_other_member(other_member_client):
    """soraには提出シードが無いため、同じ3件が全て未提出になる。"""
    response = other_member_client.get("/api/assignments")

    items = response.json()["assignments"]
    assert len(items) == 3
    assert all(item["status"] == "not_submitted" for item in items)


def test_admin_sees_all_assignments_as_not_submitted(admin_client):
    """講師には提出が無いため、一覧は常にnot_submittedになる(レスポンス形状はロールで変えない)。"""
    response = admin_client.get("/api/assignments")

    items = response.json()["assignments"]
    assert len(items) == 3
    assert all(item["status"] == "not_submitted" for item in items)


def test_seeded_reviewed_assignment_detail_includes_feedback(client):
    list_items = client.get("/api/assignments").json()["assignments"]
    reviewed_id = next(item["id"] for item in list_items if item["status"] == "reviewed")

    response = client.get(f"/api/assignments/{reviewed_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reviewed"
    assert body["submission"]["feedbackComment"]
    assert body["submission"]["feedbackAt"]


def test_seeded_reviewed_assignment_detail_is_not_submitted_for_other_member(
    client, other_member_client
):
    list_items = client.get("/api/assignments").json()["assignments"]
    reviewed_id = next(item["id"] for item in list_items if item["status"] == "reviewed")

    response = other_member_client.get(f"/api/assignments/{reviewed_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_submitted"
    assert body["submission"] is None


def test_get_assignment_detail_not_found_returns_404(client):
    response = client.get("/api/assignments/999999")

    assert response.status_code == 404


# --- 課題作成(講師のみ) ---


def test_create_assignment_appears_first_in_list(admin_client, client):
    created = _create_assignment(admin_client, title="配属先の業務フローを説明しよう")

    assert created["status"] == "not_submitted"
    assert created["submission"] is None

    items = client.get("/api/assignments").json()["assignments"]
    assert items[0]["id"] == created["id"]
    assert items[0]["title"] == "配属先の業務フローを説明しよう"


def test_member_cannot_create_assignment_returns_403(client):
    response = client.post("/api/assignments", json={"title": "タイトル", "body": "本文"})

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


def test_create_assignment_empty_title_returns_422(admin_client):
    response = admin_client.post("/api/assignments", json={"title": "  ", "body": "本文"})

    assert response.status_code == 422


def test_create_assignment_empty_body_returns_422(admin_client):
    response = admin_client.post("/api/assignments", json={"title": "タイトル", "body": ""})

    assert response.status_code == 422


# --- 回答提出(新入社員のみ) ---


def test_submit_answer_transitions_to_submitted(admin_client, client):
    created = _create_assignment(admin_client)

    response = client.post(
        f"/api/assignments/{created['id']}/submission",
        json={"answerText": "最初の回答"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "submitted"
    assert body["submission"]["answerText"] == "最初の回答"
    assert body["submission"]["feedbackComment"] is None


def test_admin_cannot_submit_answer_returns_403(admin_client):
    created = _create_assignment(admin_client)

    response = admin_client.post(
        f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"}
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


def test_resubmit_before_feedback_overwrites_answer(admin_client, client):
    created = _create_assignment(admin_client)
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "最初の回答"})

    response = client.post(
        f"/api/assignments/{created['id']}/submission",
        json={"answerText": "書き直した回答"},
    )

    assert response.status_code == 200
    assert response.json()["submission"]["answerText"] == "書き直した回答"


def test_submissions_are_isolated_between_members(admin_client, client, other_member_client):
    created = _create_assignment(admin_client)
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "ユウキの回答"})

    yuki_detail = client.get(f"/api/assignments/{created['id']}").json()
    sora_detail = other_member_client.get(f"/api/assignments/{created['id']}").json()

    assert yuki_detail["status"] == "submitted"
    assert sora_detail["status"] == "not_submitted"
    assert sora_detail["submission"] is None


def test_submit_answer_empty_text_returns_422(admin_client, client):
    created = _create_assignment(admin_client)

    response = client.post(
        f"/api/assignments/{created['id']}/submission", json={"answerText": " "}
    )

    assert response.status_code == 422


def test_submit_answer_missing_assignment_returns_404(client):
    response = client.post(
        "/api/assignments/999999/submission", json={"answerText": "回答"}
    )

    assert response.status_code == 404


def test_resubmit_after_reviewed_returns_409(admin_client, client):
    created = _create_assignment(admin_client)
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"})
    admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{_yuki_id(client)}/feedback",
        json={"comment": "コメント"},
    )

    response = client.post(
        f"/api/assignments/{created['id']}/submission",
        json={"answerText": "差し替えたい回答"},
    )

    assert response.status_code == 409


def _yuki_id(client) -> int:
    return client.get("/api/auth/me").json()["id"]


# --- 提出一覧(講師のみ) ---


def test_list_member_submissions_requires_admin(client):
    created_id = client.get("/api/assignments").json()["assignments"][0]["id"]

    response = client.get(f"/api/assignments/{created_id}/submissions")

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


def test_list_member_submissions_includes_not_submitted_members_sorted_by_name(
    admin_client, client
):
    created = _create_assignment(admin_client)
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "ユウキの回答"})

    response = admin_client.get(f"/api/assignments/{created['id']}/submissions")

    assert response.status_code == 200
    submissions = response.json()["submissions"]
    assert [item["user"]["displayName"] for item in submissions] == ["ソラ", "ハルカ", "ユウキ"]
    statuses = {item["user"]["displayName"]: item["status"] for item in submissions}
    assert statuses == {"ソラ": "not_submitted", "ハルカ": "not_submitted", "ユウキ": "submitted"}
    yuki_submission = next(item for item in submissions if item["user"]["displayName"] == "ユウキ")
    assert yuki_submission["submission"]["answerText"] == "ユウキの回答"
    others_without_submission = [
        item for item in submissions if item["user"]["displayName"] != "ユウキ"
    ]
    assert all(item["submission"] is None for item in others_without_submission)


def test_list_member_submissions_missing_assignment_returns_404(admin_client):
    response = admin_client.get("/api/assignments/999999/submissions")

    assert response.status_code == 404


def test_list_member_submissions_checks_role_before_existence(client):
    """存在しない課題でも、新入社員が呼べば先に403になる(認可>存在確認の順序)。"""
    response = client.get("/api/assignments/999999/submissions")

    assert response.status_code == 403


# --- フィードバック(講師のみ) ---


def test_feedback_transitions_to_reviewed(admin_client, client):
    created = _create_assignment(admin_client)
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"})
    yuki_id = _yuki_id(client)

    response = admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "よく書けています"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == yuki_id
    assert body["status"] == "reviewed"
    assert body["submission"]["feedbackComment"] == "よく書けています"
    assert body["submission"]["feedbackAt"]

    detail = client.get(f"/api/assignments/{created['id']}").json()
    assert detail["submission"]["feedbackComment"] == "よく書けています"


def test_feedback_is_visible_only_to_target_member(
    admin_client, client, other_member_client
):
    """yuki・sora双方が提出済みでも、yukiへのフィードバックはsora側に漏れない。"""
    created = _create_assignment(admin_client)
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "yukiの回答"})
    other_member_client.post(
        f"/api/assignments/{created['id']}/submission", json={"answerText": "soraの回答"}
    )
    yuki_id = _yuki_id(client)
    admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "コメント"},
    )

    sora_detail = other_member_client.get(f"/api/assignments/{created['id']}").json()

    assert sora_detail["status"] == "submitted"
    assert sora_detail["submission"]["feedbackComment"] is None


def test_feedback_can_be_overwritten(admin_client, client):
    created = _create_assignment(admin_client)
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"})
    yuki_id = _yuki_id(client)
    admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "最初のコメント"},
    )

    response = admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "修正したコメント"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reviewed"
    assert body["submission"]["feedbackComment"] == "修正したコメント"


def test_feedback_empty_comment_returns_422(admin_client, client):
    created = _create_assignment(admin_client)
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"})
    yuki_id = _yuki_id(client)

    response = admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": ""},
    )

    assert response.status_code == 422


def test_feedback_missing_assignment_returns_404(admin_client, client):
    yuki_id = _yuki_id(client)

    response = admin_client.post(
        f"/api/assignments/999999/submissions/{yuki_id}/feedback",
        json={"comment": "コメント"},
    )

    assert response.status_code == 404


def test_feedback_unknown_user_returns_404(admin_client):
    created = _create_assignment(admin_client)

    response = admin_client.post(
        f"/api/assignments/{created['id']}/submissions/999999/feedback",
        json={"comment": "コメント"},
    )

    assert response.status_code == 404


def test_feedback_to_admin_user_returns_404(admin_client):
    """フィードバック対象は`role == member`のみ。講師自身のuser_idは対象外(404)。"""
    created = _create_assignment(admin_client)
    admin_id = admin_client.get("/api/auth/me").json()["id"]

    response = admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{admin_id}/feedback",
        json={"comment": "コメント"},
    )

    assert response.status_code == 404


def test_feedback_without_submission_returns_409(admin_client, client):
    created = _create_assignment(admin_client)
    yuki_id = _yuki_id(client)

    response = admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "コメント"},
    )

    assert response.status_code == 409


def test_member_cannot_give_feedback_returns_403(client):
    created_id = client.get("/api/assignments").json()["assignments"][0]["id"]
    yuki_id = _yuki_id(client)

    response = client.post(
        f"/api/assignments/{created_id}/submissions/{yuki_id}/feedback",
        json={"comment": "コメント"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


# --- 個人宛て課題(target/messageForMember)の可視性 ---
#
# 手動作成(POST /api/assignments)は全員宛てのみのため、個人宛て課題は
# 課題案の配信(POST /api/assignment-proposals/{id}/approve)経由で作る。


def _create_personal_assignment(admin_client, target_client, message_for_member="頑張って"):
    target_id = target_client.get("/api/auth/me").json()["id"]
    created = admin_client.post(
        "/api/assignment-proposals", json={"userId": target_id}
    ).json()
    approved = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={
            "title": "個人宛て課題",
            "body": "個人宛ての本文",
            "messageForMember": message_for_member,
        },
    ).json()
    return approved["assignmentId"], target_id


def test_all_member_assignment_has_null_target_for_everyone(admin_client, client):
    created = _create_assignment(admin_client)

    admin_view = admin_client.get(f"/api/assignments/{created['id']}").json()
    member_view = client.get(f"/api/assignments/{created['id']}").json()

    assert admin_view["target"] is None
    assert admin_view["messageForMember"] is None
    assert member_view["target"] is None

    list_item = next(
        item for item in client.get("/api/assignments").json()["assignments"]
        if item["id"] == created["id"]
    )
    assert list_item["target"] is None


def test_personal_assignment_detail_shows_target_and_message_for_member(
    admin_client, other_member_client
):
    assignment_id, sora_id = _create_personal_assignment(admin_client, other_member_client)

    admin_detail = admin_client.get(f"/api/assignments/{assignment_id}").json()
    sora_detail = other_member_client.get(f"/api/assignments/{assignment_id}").json()

    assert admin_detail["target"] == {"id": sora_id, "displayName": "ソラ"}
    assert admin_detail["messageForMember"] == "頑張って"
    assert sora_detail["target"] == {"id": sora_id, "displayName": "ソラ"}
    assert sora_detail["messageForMember"] == "頑張って"

    list_item = next(
        item
        for item in other_member_client.get("/api/assignments").json()["assignments"]
        if item["id"] == assignment_id
    )
    assert list_item["target"] == {"id": sora_id, "displayName": "ソラ"}


def test_personal_assignment_shows_target_in_admin_list(admin_client, other_member_client):
    """観点: 講師の一覧では配信先(対象者名)が見える。"""
    assignment_id, sora_id = _create_personal_assignment(admin_client, other_member_client)

    list_item = next(
        item
        for item in admin_client.get("/api/assignments").json()["assignments"]
        if item["id"] == assignment_id
    )

    assert list_item["target"] == {"id": sora_id, "displayName": "ソラ"}


def test_assignment_list_item_and_detail_key_sets_do_not_leak_origin_or_proposal_id(
    admin_client, client
):
    """観点: 課題一覧・詳細のキー集合は固定で、由来(手動/AI課題案)を示す項目は出さない
    (`target`・`messageForMember`のみが追加項目)。"""
    created = _create_assignment(admin_client)

    list_item = next(
        item
        for item in client.get("/api/assignments").json()["assignments"]
        if item["id"] == created["id"]
    )
    detail = client.get(f"/api/assignments/{created['id']}").json()

    assert set(list_item.keys()) == {"id", "title", "status", "createdAt", "target"}
    assert set(detail.keys()) == {
        "id",
        "title",
        "body",
        "status",
        "createdAt",
        "submission",
        "target",
        "messageForMember",
    }


def test_personal_assignment_blank_message_for_member_is_null(admin_client, other_member_client):
    assignment_id, _sora_id = _create_personal_assignment(
        admin_client, other_member_client, message_for_member=""
    )

    detail = other_member_client.get(f"/api/assignments/{assignment_id}").json()

    assert detail["messageForMember"] is None


def test_personal_assignment_is_hidden_from_other_member_list(
    admin_client, other_member_client, client
):
    assignment_id, _sora_id = _create_personal_assignment(admin_client, other_member_client)

    yuki_list = client.get("/api/assignments").json()["assignments"]

    assert all(item["id"] != assignment_id for item in yuki_list)


def test_personal_assignment_detail_returns_404_for_other_member(
    admin_client, other_member_client, client
):
    assignment_id, _sora_id = _create_personal_assignment(admin_client, other_member_client)

    response = client.get(f"/api/assignments/{assignment_id}")

    assert response.status_code == 404


def test_personal_assignment_submission_returns_404_for_other_member(
    admin_client, other_member_client, client
):
    assignment_id, _sora_id = _create_personal_assignment(admin_client, other_member_client)

    response = client.post(
        f"/api/assignments/{assignment_id}/submission", json={"answerText": "回答"}
    )

    assert response.status_code == 404


def test_personal_assignment_admin_detail_is_visible_regardless_of_target(
    admin_client, other_member_client
):
    """講師は個人宛て課題でも(対象外であっても)詳細を参照できる(管理者権限は制限しない)。"""
    assignment_id, _sora_id = _create_personal_assignment(admin_client, other_member_client)

    response = admin_client.get(f"/api/assignments/{assignment_id}")

    assert response.status_code == 200


def test_personal_assignment_is_submittable_and_reviewable_for_target_member(
    admin_client, other_member_client
):
    assignment_id, sora_id = _create_personal_assignment(admin_client, other_member_client)

    submit_response = other_member_client.post(
        f"/api/assignments/{assignment_id}/submission", json={"answerText": "ソラの回答"}
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"

    submissions = admin_client.get(f"/api/assignments/{assignment_id}/submissions").json()[
        "submissions"
    ]
    assert [item["user"]["displayName"] for item in submissions] == ["ソラ"]

    feedback_response = admin_client.post(
        f"/api/assignments/{assignment_id}/submissions/{sora_id}/feedback",
        json={"comment": "良い回答です"},
    )
    assert feedback_response.status_code == 200
    assert feedback_response.json()["status"] == "reviewed"


def test_personal_assignment_feedback_for_non_target_member_returns_404(
    admin_client, other_member_client, client
):
    assignment_id, sora_id = _create_personal_assignment(admin_client, other_member_client)
    other_member_client.post(
        f"/api/assignments/{assignment_id}/submission", json={"answerText": "回答"}
    )
    yuki_id = _yuki_id(client)

    response = admin_client.post(
        f"/api/assignments/{assignment_id}/submissions/{yuki_id}/feedback",
        json={"comment": "コメント"},
    )

    assert response.status_code == 404
