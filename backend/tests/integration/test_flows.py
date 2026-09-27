"""総合テスト: 承認済みテスト観点(docs/test-perspectives.md)に対応するAPI結合フロー。

!NOTE: フロントエンドの画面操作を伴う総合的な確認は docs/manual-test-cases.md の
       手動確認で担保する（フロントエンドの自動単体テスト基盤(Vitest)は導入済みだが、
       画面操作を伴う総合テストの自動化(E2E等)は行わない方針のため）。
       ここではフロントの各画面が呼び出すAPI呼び出しの並びを、実際の画面操作の
       順序通りに再現し、複数エンドポイントをまたいだ結合的な振る舞いを確認する。
"""

import caliboo_api.db as db
from caliboo_api.models import Assignment, AssignmentSubmission, PocRun, Report


def test_home_screen_flow(client):
    """観点: ホーム画面(1b)の初期表示データが正しく返る。"""
    response = client.get("/api/home/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["streakDays"] > 0
    assert len(body["shortcuts"]) == 3
    for shortcut in body["shortcuts"]:
        assert shortcut["to"] in {"/report", "/study", "/ojt"}


def test_report_draft_then_submit_flow(client):
    """観点: 日報KPT画面(1c)で下書き保存→提出する、の順で送信できる。"""
    draft_payload = {
        "date": "2026-07-16",
        "keep": "テストを先に書けた",
        "problem": "レビュー待ちで手が止まった",
        "try": "並行タスクに着手する",
        "mood": ["fun", "tired"],
        "moodComment": "褒められて嬉しかった",
        "status": "draft",
    }
    draft_response = client.post("/api/report", json=draft_payload)
    assert draft_response.status_code == 200
    assert draft_response.json()["status"] == "draft"

    submit_payload = {**draft_payload, "status": "submitted"}
    submit_response = client.post("/api/report", json=submit_payload)
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"
    assert submit_response.json()["id"] != draft_response.json()["id"]


def test_report_history_reflects_submissions_flow(client):
    """観点: 日報KPT画面(1c)で複数回提出した日報が、履歴に日付降順(未選択時は空欄相当の空配列)で反映される。"""
    # 下書きは履歴に含まれないことを確認する
    draft_payload = {
        "date": "2026-07-19",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "mood": ["happy"],
        "moodComment": "comment",
        "status": "draft",
    }
    client.post("/api/report", json=draft_payload)

    # 感じたこと未選択の提出(空欄相当)
    submit_without_mood_payload = {
        "date": "2026-07-20",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "submitted",
    }
    client.post("/api/report", json=submit_without_mood_payload)

    # 同一日付で複数回提出した場合の順序(新しい方が先)を確認する
    submit_payload_1 = {
        "date": "2026-07-21",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "mood": ["fun"],
        "moodComment": "comment",
        "status": "submitted",
    }
    submit_payload_2 = {**submit_payload_1, "mood": ["tired"]}
    client.post("/api/report", json=submit_payload_1)
    client.post("/api/report", json=submit_payload_2)

    history = client.get("/api/report/history").json()["history"]

    assert history == [
        {
            "date": "2026-07-21",
            "keep": "keep",
            "problem": "problem",
            "try": "try",
            "mood": ["tired"],
            "moodComment": "comment",
        },
        {
            "date": "2026-07-21",
            "keep": "keep",
            "problem": "problem",
            "try": "try",
            "mood": ["fun"],
            "moodComment": "comment",
        },
        {
            "date": "2026-07-20",
            "keep": "keep",
            "problem": "problem",
            "try": "try",
            "mood": [],
            "moodComment": "",
        },
    ]


def test_report_draft_list_edit_and_delete_flow(client):
    """観点: 日報KPT画面(1c)で保存した下書きを一覧から選び、編集→再保存→提出、不要な下書きを削除できる。"""
    first_draft_payload = {
        "date": "2026-07-25",
        "keep": "keep1",
        "problem": "problem1",
        "try": "try1",
        "status": "draft",
    }
    second_draft_payload = {
        "date": "2026-07-26",
        "keep": "keep2",
        "problem": "problem2",
        "try": "try2",
        "status": "draft",
    }
    client.post("/api/report", json=first_draft_payload)
    client.post("/api/report", json=second_draft_payload)

    drafts = client.get("/api/report/drafts").json()["drafts"]
    assert [d["date"] for d in drafts] == ["2026-07-26", "2026-07-25"]

    # 一覧から古い方の下書きを選び、内容を編集して元の日付のまま保存する
    selected = drafts[1]
    assert selected["date"] == "2026-07-25"
    edited_payload = {
        "date": selected["date"],
        "keep": "keep1-edited",
        "problem": selected["problem"],
        "try": selected["try"],
        "status": "draft",
    }
    client.post("/api/report", json=edited_payload)

    # 「編集して再保存」は既存行の更新ではなく新規INSERTのため、この時点で
    # 編集後(keep1-edited)・編集前(keep1)・別日(keep2)の3件が下書きとして残る。
    drafts_after_edit = client.get("/api/report/drafts").json()["drafts"]
    assert len(drafts_after_edit) == 3
    assert drafts_after_edit[0]["date"] == "2026-07-25"
    assert drafts_after_edit[0]["keep"] == "keep1-edited"

    # 編集後の内容を提出する(元の日付のまま履歴に反映される)
    submit_payload = {**edited_payload, "status": "submitted"}
    submit_response = client.post("/api/report", json=submit_payload)
    assert submit_response.status_code == 200
    history_dates = [item["date"] for item in client.get("/api/report/history").json()["history"]]
    assert "2026-07-25" in history_dates

    # 提出後、不要になった下書き3件(編集後・編集前・別日)をすべて削除する
    for draft in drafts_after_edit:
        delete_response = client.delete(f"/api/report/drafts/{draft['id']}")
        assert delete_response.status_code == 204

    final_drafts = client.get("/api/report/drafts").json()["drafts"]
    assert final_drafts == []

    # 提出済みレコードは下書き削除エンドポイントでは削除できない(404)
    submitted_id = int(submit_response.json()["id"].rsplit("_", 1)[-1])
    forbidden_delete_response = client.delete(f"/api/report/drafts/{submitted_id}")
    assert forbidden_delete_response.status_code == 404


def test_ojt_department_select_and_chat_flow(client):
    """観点: OJT画面(1e/1f)で課一覧取得→課選択→初期メッセージ・ナレッジ取得→チャット送信。"""
    departments = client.get("/api/ojt/departments").json()["departments"]
    dept_id = departments[0]["id"]
    dept_name = departments[0]["name"]

    messages_response = client.get(f"/api/ojt/departments/{dept_id}/messages")
    assert messages_response.status_code == 200
    assert messages_response.json()["messages"][0]["role"] == "bot"

    knowledge_response = client.get(f"/api/ojt/departments/{dept_id}/knowledge")
    assert knowledge_response.status_code == 200
    assert len(knowledge_response.json()["items"]) >= 1

    chat_response = client.post(
        "/api/ojt/chat", json={"deptId": dept_id, "text": "よく聞かれる質問は？"}
    )
    assert chat_response.status_code == 200
    assert dept_name in chat_response.json()["text"]


def test_ojt_switch_department_updates_context(client):
    """観点: OJT画面(1f)で課を切り替えると中央チャット・右ナレッジの対象課が変わる。"""
    departments = client.get("/api/ojt/departments").json()["departments"]
    first_id, second_id = departments[0]["id"], departments[1]["id"]

    first_knowledge = client.get(f"/api/ojt/departments/{first_id}/knowledge").json()
    second_knowledge = client.get(f"/api/ojt/departments/{second_id}/knowledge").json()

    assert first_knowledge["deptId"] == first_id
    assert second_knowledge["deptId"] == second_id
    assert first_knowledge["items"] != second_knowledge["items"]


def test_quiz_answer_then_next_question_flow(client):
    """観点: 資格勉強画面(2a)で出題→解答→次の問題、を繰り返せる。"""
    first_question = client.get("/api/quiz/next").json()
    assert "correctIndex" not in first_question

    correct_answer = client.post(
        "/api/quiz/answer",
        json={"questionId": first_question["id"], "selectedIndex": 1},
    ).json()
    assert "correct" in correct_answer

    second_question = client.get(
        "/api/quiz/next", params={"category": first_question["category"]}
    ).json()
    assert second_question["category"] == first_question["category"]


def test_quiz_next_question_excludes_previous_question_flow(client):
    """観点: 資格勉強画面(2a)で「次の問題」を繰り返し押しても、直前の問題が連続して出題されない。"""
    current = client.get("/api/quiz/next", params={"category": "technology"}).json()

    for _ in range(20):
        next_question = client.get(
            "/api/quiz/next",
            params={"category": "technology", "excludeId": current["id"]},
        ).json()
        assert next_question["id"] != current["id"]
        current = next_question


def test_quiz_question_source_display_flow(client):
    """観点: 出典(source)を持つ問題では出典表示があり、サンプル問題(出典なし)では表示されない。"""
    seen_sources = set()
    exclude_id = None
    for _ in range(30):
        params = {"category": "technology"}
        if exclude_id:
            params["excludeId"] = exclude_id
        question = client.get("/api/quiz/next", params=params).json()
        seen_sources.add(question.get("source"))
        exclude_id = question["id"]

    assert None in seen_sources
    assert any(source is not None for source in seen_sources)


def test_quiz_category_filter_flow(client):
    """観点: 資格勉強画面(2a)でサイドバーの分野クリックにより出題分野が切り替わる。"""
    management_question = client.get("/api/quiz/next", params={"category": "management"}).json()
    strategy_question = client.get("/api/quiz/next", params={"category": "strategy"}).json()

    assert management_question["category"] == "management"
    assert strategy_question["category"] == "strategy"


def test_study_chat_flow(client):
    """観点: 資格勉強画面(2b)で関連過去問一覧取得→チャット送信ができる。"""
    related = client.get("/api/study/related-questions")
    assert related.status_code == 200
    assert len(related.json()["items"]) >= 1

    chat_response = client.post("/api/study/chat", json={"text": "TCPとUDPの違いは？"})
    assert chat_response.status_code == 200
    assert chat_response.json()["role"] == "bot"


def test_unknown_department_returns_404(client):
    """観点: 存在しないdeptIdを指定した場合に404が返る。"""
    assert client.get("/api/ojt/departments/unknown/messages").status_code == 404
    assert client.get("/api/ojt/departments/unknown/knowledge").status_code == 404
    assert client.post("/api/ojt/chat", json={"deptId": "unknown", "text": "hi"}).status_code == 404


def test_unknown_question_returns_404(client):
    """観点: 存在しないquestionIdを指定した場合に404が返る。"""
    response = client.post(
        "/api/quiz/answer", json={"questionId": "unknown", "selectedIndex": 0}
    )
    assert response.status_code == 404


def test_invalid_quiz_category_returns_422(client):
    """観点: 不正なカテゴリ指定時に422が返る。"""
    response = client.get("/api/quiz/next", params={"category": "unknown"})
    assert response.status_code == 422


def test_report_submit_then_reload_persists_across_sessions_flow(client):
    """観点: 日報KPT画面(1c)でPOSTした内容がDBに永続化され、別セッションでも読み出せる。"""
    payload = {
        "date": "2026-07-18",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "mood": ["happy"],
        "moodComment": "comment",
        "status": "submitted",
    }

    response = client.post("/api/report", json=payload)
    assert response.status_code == 200
    body = response.json()

    pk = int(body["id"].rsplit("_", 1)[-1])

    # POST時のセッションとは別の新規セッションで読み出しても保持されていることを確認する。
    with db.session_scope() as session:
        saved = session.get(Report, pk)
        assert saved is not None
        assert saved.date == "2026-07-18"
        assert saved.try_ == "try"
        assert saved.mood == ["happy"]
        assert saved.status == "submitted"
        assert saved.saved_at == body["savedAt"]


def _member_id(member_client) -> int:
    return member_client.get("/api/auth/me").json()["id"]


def test_assignment_initial_list_has_seeded_three_states_flow(client):
    """観点: yukiでログインした初期表示で未提出/レビュー待ち/フィードバック済みの3件が
    作成日時降順で一覧表示される。"""
    items = client.get("/api/assignments").json()["assignments"]

    assert len(items) == 3
    assert [item["status"] for item in items] == ["not_submitted", "submitted", "reviewed"]
    assert items == sorted(items, key=lambda item: item["createdAt"], reverse=True)


def test_assignment_create_submit_feedback_flow(admin_client, client):
    """観点: 講師が課題を作成すると一覧の先頭に「未提出」として追加され、新入社員が
    回答を提出すると「レビュー待ち」になり、講師がコメントするとその新入社員も
    コメントを読める「フィードバック済み」になる一連のフロー。"""
    create_response = admin_client.post(
        "/api/assignments", json={"title": "結合テスト用課題", "body": "課題文"}
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "not_submitted"

    list_after_create = client.get("/api/assignments").json()["assignments"]
    assert list_after_create[0]["id"] == created["id"]

    submit_response = client.post(
        f"/api/assignments/{created['id']}/submission", json={"answerText": "最初の回答"}
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"

    yuki_id = _member_id(client)
    feedback_response = admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "良い回答です"},
    )
    assert feedback_response.status_code == 200
    body = feedback_response.json()
    assert body["status"] == "reviewed"
    assert body["submission"]["feedbackComment"] == "良い回答です"

    detail_after_feedback = client.get(f"/api/assignments/{created['id']}").json()
    assert detail_after_feedback["status"] == "reviewed"
    assert detail_after_feedback["submission"]["feedbackComment"] == "良い回答です"


def test_assignment_resubmit_before_feedback_does_not_duplicate_flow(admin_client, client):
    """観点: レビュー待ちの課題は回答を上書き再提出でき、提出が重複せず提出日時のみ更新される。"""
    created = admin_client.post(
        "/api/assignments", json={"title": "再提出テスト", "body": "課題文"}
    ).json()

    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答1"})
    first_detail = client.get(f"/api/assignments/{created['id']}").json()

    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答2"})
    second_detail = client.get(f"/api/assignments/{created['id']}").json()

    assert second_detail["submission"]["answerText"] == "回答2"
    assert second_detail["status"] == "submitted"
    # 提出行が重複していないことをDB側からも確認する
    with db.session_scope() as session:
        rows = (
            session.query(AssignmentSubmission)
            .filter(AssignmentSubmission.assignment_id == created["id"])
            .all()
        )
        assert len(rows) == 1
    assert first_detail["submission"]["submittedAt"] <= second_detail["submission"]["submittedAt"]


def test_assignment_reviewed_locks_resubmission_flow(admin_client, client):
    """観点: フィードバック済みの課題への再提出は409で拒否され(UI上も入力できない想定)、
    フィードバックは上書きできる(状態は「フィードバック済み」のまま)。"""
    created = admin_client.post(
        "/api/assignments", json={"title": "ロックテスト", "body": "課題文"}
    ).json()
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"})
    yuki_id = _member_id(client)
    admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "初回コメント"},
    )

    locked_response = client.post(
        f"/api/assignments/{created['id']}/submission", json={"answerText": "差し替え回答"}
    )
    assert locked_response.status_code == 409

    overwrite_response = admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "修正コメント"},
    )
    assert overwrite_response.status_code == 200
    assert overwrite_response.json()["status"] == "reviewed"
    assert overwrite_response.json()["submission"]["feedbackComment"] == "修正コメント"


def test_assignment_feedback_without_submission_returns_409_flow(admin_client, client):
    """観点: 未提出の課題へのフィードバックは409で拒否される(UI上も入力できない想定)。"""
    created = admin_client.post(
        "/api/assignments", json={"title": "未提出テスト", "body": "課題文"}
    ).json()
    yuki_id = _member_id(client)

    response = admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "コメント"},
    )
    assert response.status_code == 409


def test_assignment_unknown_id_returns_404_flow(admin_client, client):
    """観点: 存在しない課題IDへの詳細取得・提出・提出一覧・フィードバックは404になる。"""
    yuki_id = _member_id(client)
    assert client.get("/api/assignments/999999").status_code == 404
    assert (
        client.post("/api/assignments/999999/submission", json={"answerText": "回答"}).status_code
        == 404
    )
    assert admin_client.get("/api/assignments/999999/submissions").status_code == 404
    assert (
        admin_client.post(
            f"/api/assignments/999999/submissions/{yuki_id}/feedback",
            json={"comment": "コメント"},
        ).status_code
        == 404
    )


def test_assignment_blank_fields_return_422_flow(admin_client, client):
    """観点: タイトル・課題文・回答・コメントが空の場合は422になる。"""
    assert (
        admin_client.post("/api/assignments", json={"title": " ", "body": "本文"}).status_code
        == 422
    )
    assert (
        admin_client.post(
            "/api/assignments", json={"title": "タイトル", "body": ""}
        ).status_code
        == 422
    )

    created = admin_client.post(
        "/api/assignments", json={"title": "バリデーションテスト", "body": "課題文"}
    ).json()
    assert (
        client.post(
            f"/api/assignments/{created['id']}/submission", json={"answerText": " "}
        ).status_code
        == 422
    )
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"})
    yuki_id = _member_id(client)
    assert (
        admin_client.post(
            f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
            json={"comment": ""},
        ).status_code
        == 422
    )


def test_assignment_persists_across_sessions_flow(admin_client, client):
    """観点: 提出内容・フィードバックがDB永続化され、サーバ再起動相当の別セッションでも保持される。"""
    created = admin_client.post(
        "/api/assignments", json={"title": "永続化テスト", "body": "課題文"}
    ).json()
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"})
    yuki_id = _member_id(client)
    admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "コメント"},
    )

    with db.session_scope() as session:
        assignment = session.get(Assignment, created["id"])
        assert assignment is not None
        submission = (
            session.query(AssignmentSubmission)
            .filter(AssignmentSubmission.assignment_id == created["id"])
            .one()
        )
        assert submission.feedback_comment == "コメント"


def test_assignment_status_is_per_member_flow(admin_client, client, other_member_client):
    """観点: 一覧・詳細の状態は本人の提出に基づく(yukiが提出してもsoraの状態は
    「未提出」のまま)。"""
    created = admin_client.post(
        "/api/assignments", json={"title": "分離確認テスト", "body": "課題文"}
    ).json()
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"})

    sora_detail = other_member_client.get(f"/api/assignments/{created['id']}").json()
    assert sora_detail["status"] == "not_submitted"
    assert sora_detail["submission"] is None

    sora_list_item = next(
        item
        for item in other_member_client.get("/api/assignments").json()["assignments"]
        if item["id"] == created["id"]
    )
    assert sora_list_item["status"] == "not_submitted"


def test_assignment_role_permissions_flow(admin_client, client):
    """観点: 課題を作成できるのは講師のみ・提出できるのは新入社員のみ・提出一覧と
    フィードバックを扱えるのは講師のみ。ロールが逆の場合は403になる。"""
    assert (
        client.post(
            "/api/assignments", json={"title": "権限テスト", "body": "本文"}
        ).status_code
        == 403
    )

    created = admin_client.post(
        "/api/assignments", json={"title": "権限テスト", "body": "本文"}
    ).json()
    assert (
        admin_client.post(
            f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"}
        ).status_code
        == 403
    )
    assert client.get(f"/api/assignments/{created['id']}/submissions").status_code == 403

    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"})
    yuki_id = _member_id(client)
    assert (
        client.post(
            f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
            json={"comment": "コメント"},
        ).status_code
        == 403
    )


def test_assignment_submissions_list_and_feedback_visibility_flow(
    admin_client, client, other_member_client
):
    """観点: 講師は課題詳細で新入社員全員(未提出者を含む)の状態・回答を一覧でき、
    新入社員ごとのフィードバックは当該の新入社員にのみ表示される(他の新入社員が
    提出済みでもフィードバックは漏れない)。"""
    created = admin_client.post(
        "/api/assignments", json={"title": "一覧確認テスト", "body": "課題文"}
    ).json()
    client.post(f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"})

    submissions = admin_client.get(
        f"/api/assignments/{created['id']}/submissions"
    ).json()["submissions"]
    assert [item["user"]["displayName"] for item in submissions] == ["ソラ", "ハルカ", "ユウキ"]
    assert {item["user"]["displayName"]: item["status"] for item in submissions} == {
        "ソラ": "not_submitted",
        "ハルカ": "not_submitted",
        "ユウキ": "submitted",
    }

    other_member_client.post(
        f"/api/assignments/{created['id']}/submission", json={"answerText": "回答"}
    )

    yuki_id = _member_id(client)
    admin_client.post(
        f"/api/assignments/{created['id']}/submissions/{yuki_id}/feedback",
        json={"comment": "ユウキ宛のコメント"},
    )

    yuki_detail = client.get(f"/api/assignments/{created['id']}").json()
    assert yuki_detail["submission"]["feedbackComment"] == "ユウキ宛のコメント"
    sora_detail = other_member_client.get(f"/api/assignments/{created['id']}").json()
    assert sora_detail["status"] == "submitted"
    assert sora_detail["submission"]["feedbackComment"] is None


def test_assignment_feedback_unknown_or_non_member_user_returns_404_flow(admin_client):
    """観点: 存在しないuserId・講師のuserIdへのフィードバックは404になる。"""
    created = admin_client.post(
        "/api/assignments", json={"title": "対象確認テスト", "body": "課題文"}
    ).json()
    admin_id = admin_client.get("/api/auth/me").json()["id"]

    assert (
        admin_client.post(
            f"/api/assignments/{created['id']}/submissions/999999/feedback",
            json={"comment": "コメント"},
        ).status_code
        == 404
    )
    assert (
        admin_client.post(
            f"/api/assignments/{created['id']}/submissions/{admin_id}/feedback",
            json={"comment": "コメント"},
        ).status_code
        == 404
    )


def test_assignment_proposal_generate_edit_approve_visibility_flow(
    admin_client, third_member_client, client, other_member_client
):
    """観点: 講師が新入社員を選んで課題案をつくると確認待ちの課題案ができ、編集して
    配信すると編集後の内容で課題が作成される。配信した課題は対象の新入社員の一覧に
    だけ出て、提出→フィードバックの流れは通常の課題と同じになる。"""
    haruka_id = third_member_client.get("/api/auth/me").json()["id"]

    created = admin_client.post(
        "/api/assignment-proposals", json={"userId": haruka_id}
    ).json()
    assert created["status"] == "pending"
    assert created["target"] == {"id": haruka_id, "displayName": "ハルカ"}
    # ハルカのシードは「報告の構成」テーマを引くように投入している(report_seed.py)。
    assert created["title"] == "報告の構成を整理してみよう"
    assert any(material["kind"] == "mood" for material in created["materials"])

    approved = admin_client.post(
        f"/api/assignment-proposals/{created['id']}/approve",
        json={
            "title": "報告のふりかえり課題(編集版)",
            "body": "編集後の課題文",
            "messageForMember": "一緒に練習しましょう",
        },
    ).json()
    assert approved["status"] == "approved"
    assert approved["edited"] is True
    assignment_id = approved["assignmentId"]

    haruka_list = third_member_client.get("/api/assignments").json()["assignments"]
    assert any(item["id"] == assignment_id for item in haruka_list)
    yuki_list = client.get("/api/assignments").json()["assignments"]
    sora_list = other_member_client.get("/api/assignments").json()["assignments"]
    assert all(item["id"] != assignment_id for item in yuki_list)
    assert all(item["id"] != assignment_id for item in sora_list)

    assert other_member_client.get(f"/api/assignments/{assignment_id}").status_code == 404
    assert (
        other_member_client.post(
            f"/api/assignments/{assignment_id}/submission", json={"answerText": "回答"}
        ).status_code
        == 404
    )

    submit_response = third_member_client.post(
        f"/api/assignments/{assignment_id}/submission", json={"answerText": "ハルカの回答"}
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"
    assert submit_response.json()["messageForMember"] == "一緒に練習しましょう"

    submissions = admin_client.get(f"/api/assignments/{assignment_id}/submissions").json()[
        "submissions"
    ]
    assert [item["user"]["displayName"] for item in submissions] == ["ハルカ"]

    feedback_response = admin_client.post(
        f"/api/assignments/{assignment_id}/submissions/{haruka_id}/feedback",
        json={"comment": "結論から話せていて良いです"},
    )
    assert feedback_response.status_code == 200
    assert feedback_response.json()["status"] == "reviewed"

    haruka_detail = third_member_client.get(f"/api/assignments/{assignment_id}").json()
    assert haruka_detail["submission"]["feedbackComment"] == "結論から話せていて良いです"


def test_assignment_proposal_reject_then_regenerate_excludes_theme_flow(
    admin_client, other_member_client
):
    """観点: 見送ると課題案は「見送り」になり課題は作成されない。その新入社員に
    見送り済みのテーマは次の課題案で選ばれない。"""
    sora_id = other_member_client.get("/api/auth/me").json()["id"]
    with db.session_scope() as session:
        session.add(
            Report(
                user_id=sora_id,
                date="2026-09-20",
                keep="特に無い。",
                problem="Gitのブランチ運用で戸惑った。",
                try_="次はブランチ運用を復習する。",
                mood=[],
                mood_comment="特に無い。",
                status="submitted",
                saved_at="2026-09-20T18:00:00+00:00",
            )
        )
        session.commit()

    first = admin_client.post("/api/assignment-proposals", json={"userId": sora_id}).json()
    assert first["title"] == "Gitのブランチ運用を整理しよう"

    reject_response = admin_client.post(
        f"/api/assignment-proposals/{first['id']}/reject", json={"reason": "様子見"}
    )
    assert reject_response.status_code == 200
    rejected = reject_response.json()
    assert rejected["status"] == "rejected"
    assert rejected["assignmentId"] is None

    second = admin_client.post("/api/assignment-proposals", json={"userId": sora_id}).json()
    assert second["id"] != first["id"]
    assert second["title"] != "Gitのブランチ運用を整理しよう"


def test_login_logout_flow(anonymous_client):
    """観点: 開発用アカウントでログインでき、以後の保護APIが呼べる。ログアウトすると
    APIが401になり、`/api/auth/login`・`/api/auth/logout`以外は未認証で401になる。
    ログアウトはサーバー側のセッションも破棄し、ログアウト前のトークンを使い回しても
    保護APIは401になる(Cookieを消すだけの見せかけのログアウトではないことの確認)。"""
    assert anonymous_client.get("/api/home/summary").status_code == 401

    login_response = anonymous_client.post(
        "/api/auth/login", json={"loginId": "yuki", "password": "caliboo-yuki"}
    )
    assert login_response.status_code == 200
    assert login_response.json()["displayName"] == "ユウキ"

    assert anonymous_client.get("/api/home/summary").status_code == 200
    assert anonymous_client.get("/api/auth/me").json()["loginId"] == "yuki"

    token_before_logout = anonymous_client.cookies.get("caliboo_session")

    logout_response = anonymous_client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    assert anonymous_client.get("/api/home/summary").status_code == 401

    # ログアウト前のトークンを戻しても、サーバー側のセッションは破棄済みなので401のまま
    anonymous_client.cookies.set("caliboo_session", token_before_logout)
    assert anonymous_client.get("/api/home/summary").status_code == 401

    # Cookieが無い状態でログアウトを呼んでも(二重ログアウト等)204で成功する
    anonymous_client.cookies.delete("caliboo_session")
    assert anonymous_client.post("/api/auth/logout").status_code == 204


def test_user_data_isolation_across_screens_flow(client, other_member_client):
    """観点: ホーム・資格勉強・日報の各画面で、ログイン中のユーザーのデータだけが返り、
    他人の下書き・提出は見えない(ユーザー間のデータ分離)。"""
    yuki_home = client.get("/api/home/summary").json()
    sora_home = other_member_client.get("/api/home/summary").json()
    assert yuki_home["user"]["name"] == "ユウキ"
    assert sora_home["user"]["name"] == "ソラ"
    assert yuki_home["user"]["streakDays"] != sora_home["user"]["streakDays"]

    yuki_progress = client.get("/api/study/progress").json()
    sora_progress = other_member_client.get("/api/study/progress").json()
    assert yuki_progress["streakDays"] != sora_progress["streakDays"]

    draft_payload = {
        "date": "2026-09-25",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "status": "draft",
    }
    created_draft = client.post("/api/report", json=draft_payload).json()
    draft_id = int(created_draft["id"].rsplit("_", 1)[-1])

    assert other_member_client.get("/api/report/drafts").json() == {"drafts": []}
    assert other_member_client.delete(f"/api/report/drafts/{draft_id}").status_code == 404
    assert len(client.get("/api/report/drafts").json()["drafts"]) == 1


def test_strength_analysis_run_flow(client):
    """観点: 強み解析PoCのパイプラインが1 runで通り、各部分が取得できる。"""
    personas = client.get("/api/poc/personas").json()["personas"]
    assert [persona["personaKey"] for persona in personas] == [
        "sql_strong_doc_weak",
        "ambiguous_signal",
        "communication_strong",
    ]

    created = client.post(
        "/api/poc/runs", json={"personaKey": "sql_strong_doc_weak"}
    ).json()
    run_id = created["id"]
    assert created["status"] == "completed"
    assert len(created["trajectory"]) == 3
    assert len(created["reviews"]["reviews"]) == 3
    assert created["diary"]["mentorComment"] == created["reviews"]["fanInComment"]

    assert client.get(f"/api/poc/runs/{run_id}").json() == created
    assert client.get(f"/api/poc/runs/{run_id}/diary").json() == created["diary"]
    assert client.get(f"/api/poc/runs/{run_id}/reviews").json() == created["reviews"]
    strengths = client.get(f"/api/poc/runs/{run_id}/strengths").json()
    assert strengths == created["strengths"]
    assert strengths["runId"] == run_id

    runs = client.get("/api/poc/runs").json()["runs"]
    assert [run["id"] for run in runs] == [run_id]


def test_strength_analysis_reproduces_injected_persona_flow(client):
    """観点: 既知ペルソナを注入したrunで、解析が該当スキルを確定として復元する(機構妥当性)。"""
    run = client.post(
        "/api/poc/runs", json={"personaKey": "sql_strong_doc_weak"}
    ).json()

    strengths = {
        item["layerTask"]["skillCode"]: item for item in run["strengths"]["strengths"]
    }
    assert strengths["DBAD"]["status"] == "confirmed"
    assert strengths["DBAD"]["confidence"] == 0.85
    assert {evidence["source"]["kind"] for evidence in strengths["DBAD"]["evidence"]} == {
        "trajectory",
        "diary",
        "review",
    }
    assert "DOCM" not in strengths
    assert run["strengths"]["overallStatus"] == "partial"


def test_strength_analysis_holds_back_weak_signal_flow(client):
    """観点: 信号が弱いペルソナでは断定せず、全体判定が評価保留になる(過剰付与の抑制)。"""
    run = client.post("/api/poc/runs", json={"personaKey": "ambiguous_signal"}).json()

    strengths = run["strengths"]["strengths"]
    assert strengths
    assert all(item["status"] == "insufficient_evidence" for item in strengths)
    assert all(item["layerWillSkill"] is None for item in strengths)
    assert run["strengths"]["overallStatus"] == "insufficient"


def test_strength_analysis_does_not_confuse_domains_flow(client):
    """観点: 分野の違うペルソナで、無関係な強みを付与しない(誤検出の抑制)。"""
    run = client.post(
        "/api/poc/runs", json={"personaKey": "communication_strong"}
    ).json()

    by_code = {
        item["layerTask"]["skillCode"]: item for item in run["strengths"]["strengths"]
    }
    assert by_code["RLMT"]["status"] == "confirmed"
    assert "DBAD" not in by_code
    assert "DTAN" not in by_code


def test_strength_analysis_run_persists_across_sessions_flow(client):
    """観点: runがDB永続化され、サーバ再起動相当の別セッションでも保持される。"""
    created = client.post(
        "/api/poc/runs", json={"personaKey": "sql_strong_doc_weak"}
    ).json()

    with db.session_scope() as session:
        row = session.get(PocRun, 1)
        assert row is not None
        assert row.persona_key == "sql_strong_doc_weak"
        assert row.strengths["runId"] == created["id"]
        assert len(row.trajectory) == 3


def test_strength_analysis_error_cases_flow(client):
    """観点: 未知のpersonaKey・存在しない/不正なrun IDは404になる。"""
    assert (
        client.post("/api/poc/runs", json={"personaKey": "unknown"}).status_code == 404
    )
    assert client.get("/api/poc/runs/run_9999").status_code == 404
    assert client.get("/api/poc/runs/oops/strengths").status_code == 404


def _external_import_payload():
    """POST /api/poc/runs/import用のサンプルペイロード(単体テストと同じ組み立て方)。"""
    return {
        "subjectId": "emp_101",
        "label": "Claude生成run(SQLが強い新人)",
        "trajectory": [
            {
                "iteration": 1,
                "task": {
                    "taskId": "ext_1",
                    "title": "受注データの集計",
                    "description": "受注データを集計してください。",
                    "skillHint": "DBAD",
                },
                "workerOutput": (
                    "SQLクエリを作成し、ordersテーブルとorder_itemsテーブルを"
                    "結合して月次の集計を行いました。"
                ),
                "trainerFeedback": "良い進め方です。次はダッシュボード化してみましょう。",
            },
            {
                "iteration": 2,
                "task": {
                    "taskId": "ext_2",
                    "title": "集計結果の可視化",
                    "description": "集計結果を可視化してください。",
                    "skillHint": "DTAN",
                },
                "workerOutput": "インデックスを追加してクエリの速度を改善しました。",
                "trainerFeedback": "性能を自分で切り分けられている点が良いです。",
            },
            {
                "iteration": 3,
                "task": {
                    "taskId": "ext_3",
                    "title": "引き継ぎメモの作成",
                    "description": "引き継ぎメモを作成してください。",
                    "skillHint": "DOCM",
                },
                "workerOutput": "引き継ぎメモをまとめました。",
                "trainerFeedback": "次は前提の説明を厚くしましょう。",
            },
        ],
        "diary": {
            "date": "2026-09-24",
            "tasks": [
                {
                    "time": "09:30-12:00",
                    "what": "受注データの集計クエリ作成",
                    "progressDesc": "SQLクエリを作成し検算まで実施",
                    "progressRate": 100,
                },
            ],
            "feelings": {
                "emotion": "たのしい",
                "trigger": "クエリが想定通り動いたとき",
                "nextAction": "次は可視化に着手する",
            },
            "kpt": {
                "keep": "検算してから提出する進め方を続けたい",
                "problem": "引き継ぎ資料の分量が不足している",
                "try": "初めて読む人のつもりで読み返す",
            },
        },
        "reviews": [
            {
                "agentKey": "alpha",
                "reviewerRole": "管理職",
                "magiTone": "MELCHIOR",
                "comment": "集計クエリの構成が後から見ても分かりやすい。",
                "flags": [],
            },
            {
                "agentKey": "beta",
                "reviewerRole": "講師",
                "magiTone": "BALTHASAR",
                "comment": "前回の助言を素直に反映できている。",
                "flags": [],
            },
            {
                "agentKey": "gamma",
                "reviewerRole": "シニアエンジニア",
                "magiTone": "CASPER",
                "comment": "インデックスの追加判断に地力がある。",
                "flags": [],
            },
        ],
        "trace": {
            "generationProvider": "claude_session",
            "agents": [
                {"key": "strength-worker", "model": "sonnet", "promptVersion": "2026-09-24.1"},
            ],
        },
    }


def test_strength_analysis_import_flow(client):
    """観点: 外部(Claude Codeセッション等)投入runがFan-in統合・解析を経て一覧に反映される。"""
    script_run = client.post(
        "/api/poc/runs", json={"personaKey": "ambiguous_signal"}
    ).json()

    imported = client.post("/api/poc/runs/import", json=_external_import_payload()).json()
    run_id = imported["id"]

    assert imported["status"] == "completed"
    assert imported["personaKey"] == "external_claude"
    assert imported["diary"]["mentorComment"] == imported["reviews"]["fanInComment"]
    assert imported["trace"]["agents"][0]["key"] == "strength-worker"

    strengths = client.get(f"/api/poc/runs/{run_id}/strengths").json()
    assert strengths == imported["strengths"]
    by_code = {item["layerTask"]["skillCode"]: item for item in strengths["strengths"]}
    assert by_code["DBAD"]["status"] == "confirmed"

    runs = client.get("/api/poc/runs").json()["runs"]
    assert [run["id"] for run in runs] == [run_id, script_run["id"]]


def test_strength_analysis_import_rejects_malformed_trajectory_flow(client):
    """観点: 軌跡が3周連番でない外部投入runは422になる(仕様書§5「3回固定」)。"""
    payload = _external_import_payload()
    payload["trajectory"] = payload["trajectory"][:2]

    response = client.post("/api/poc/runs/import", json=payload)

    assert response.status_code == 422
