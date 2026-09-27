import caliboo_api.db as db
from caliboo_api.data.report_data import (
    create_report,
    delete_draft,
    fetch_draft_list,
    fetch_report_history,
)
from caliboo_api.schemas.report import ReportRequest


def _make_payload(**overrides) -> ReportRequest:
    data = {
        "date": "2026-07-15",
        "keep": "keep",
        "problem": "problem",
        "try": "try",
        "mood": ["fun", "tired"],
        "moodComment": "comment",
        "status": "draft",
    }
    data.update(overrides)
    return ReportRequest.model_validate(data)


def test_create_report_assigns_pk(bootstrapped_db, user_ids):
    with db.session_scope() as session:
        report = create_report(session, user_ids["yuki"], _make_payload())

        assert report.id is not None
        assert report.user_id == user_ids["yuki"]
        assert report.date == "2026-07-15"
        assert report.try_ == "try"
        assert report.mood == ["fun", "tired"]
        assert report.status == "draft"
        assert report.saved_at


def test_create_report_ids_are_sequential(bootstrapped_db, user_ids):
    with db.session_scope() as session:
        first = create_report(session, user_ids["yuki"], _make_payload())
        second = create_report(session, user_ids["yuki"], _make_payload())

        assert second.id == first.id + 1


def test_fetch_report_history_returns_only_submitted(bootstrapped_db, user_ids):
    yuki_id = user_ids["yuki"]
    with db.session_scope() as session:
        create_report(session, yuki_id, _make_payload(status="draft"))
        create_report(session, yuki_id, _make_payload(status="submitted"))

    history = fetch_report_history(yuki_id)

    assert len(history) == 1
    assert history[0].date == "2026-07-15"


def test_fetch_report_history_includes_detail_fields(bootstrapped_db, user_ids):
    yuki_id = user_ids["yuki"]
    with db.session_scope() as session:
        create_report(
            session,
            yuki_id,
            _make_payload(
                keep="keepの内容",
                problem="problemの内容",
                **{"try": "tryの内容"},
                moodComment="moodCommentの内容",
                status="submitted",
            ),
        )

    history = fetch_report_history(yuki_id)

    assert history[0].keep == "keepの内容"
    assert history[0].problem == "problemの内容"
    assert history[0].try_ == "tryの内容"
    assert history[0].moodComment == "moodCommentの内容"


def test_fetch_report_history_orders_by_date_then_id_desc(bootstrapped_db, user_ids):
    yuki_id = user_ids["yuki"]
    with db.session_scope() as session:
        create_report(
            session, yuki_id, _make_payload(date="2026-07-10", mood=["happy"], status="submitted")
        )
        create_report(
            session, yuki_id, _make_payload(date="2026-07-18", mood=["fun"], status="submitted")
        )
        create_report(
            session, yuki_id, _make_payload(date="2026-07-18", mood=["tired"], status="submitted")
        )

    history = fetch_report_history(yuki_id)

    assert [(item.date, item.mood) for item in history] == [
        ("2026-07-18", ["tired"]),
        ("2026-07-18", ["fun"]),
        ("2026-07-10", ["happy"]),
    ]


def test_fetch_report_history_mood_matches_stored_value(bootstrapped_db, user_ids):
    yuki_id = user_ids["yuki"]
    with db.session_scope() as session:
        create_report(session, yuki_id, _make_payload(mood=["foggy"], status="submitted"))

    history = fetch_report_history(yuki_id)

    assert history[0].mood == ["foggy"]


def test_fetch_report_history_empty_list_when_no_submitted_reports(bootstrapped_db, user_ids):
    yuki_id = user_ids["yuki"]
    with db.session_scope() as session:
        create_report(session, yuki_id, _make_payload(status="draft"))

    history = fetch_report_history(yuki_id)

    assert history == []


def test_fetch_report_history_is_isolated_per_user(bootstrapped_db, user_ids):
    yuki_id, sora_id = user_ids["yuki"], user_ids["sora"]
    with db.session_scope() as session:
        create_report(session, yuki_id, _make_payload(status="submitted"))
        create_report(session, sora_id, _make_payload(date="2026-07-16", status="submitted"))

    assert len(fetch_report_history(yuki_id)) == 1
    assert len(fetch_report_history(sora_id)) == 1


def test_fetch_draft_list_is_isolated_per_user(bootstrapped_db, user_ids):
    yuki_id, sora_id = user_ids["yuki"], user_ids["sora"]
    with db.session_scope() as session:
        create_report(session, yuki_id, _make_payload(status="draft"))

    assert len(fetch_draft_list(yuki_id)) == 1
    assert fetch_draft_list(sora_id) == []


def test_delete_draft_rejects_other_users_draft(bootstrapped_db, user_ids):
    yuki_id, sora_id = user_ids["yuki"], user_ids["sora"]
    with db.session_scope() as session:
        report = create_report(session, yuki_id, _make_payload(status="draft"))

        deleted = delete_draft(session, sora_id, report.id)

    assert deleted is False


def test_delete_draft_succeeds_for_owner(bootstrapped_db, user_ids):
    yuki_id = user_ids["yuki"]
    with db.session_scope() as session:
        report = create_report(session, yuki_id, _make_payload(status="draft"))

        deleted = delete_draft(session, yuki_id, report.id)

    assert deleted is True
    assert fetch_draft_list(yuki_id) == []
