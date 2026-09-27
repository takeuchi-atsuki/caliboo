import caliboo_api.db as db
from caliboo_api.data.assignment_data import (
    FeedbackSaveError,
    SubmissionSaveError,
    create_assignment,
    fetch_assignment_list,
    fetch_member_submissions,
    get_assignment_detail,
    save_member_feedback,
    save_submission,
)
from caliboo_api.models import Assignment, AssignmentSubmission


def test_create_assignment_status_is_not_submitted(bootstrapped_db):
    with db.session_scope() as session:
        detail = create_assignment(session, "タイトル", "本文")

    assert detail.status == "not_submitted"
    assert detail.submission is None


def test_save_submission_creates_single_row(bootstrapped_db, user_ids):
    yuki_id = user_ids["yuki"]
    with db.session_scope() as session:
        created = create_assignment(session, "タイトル", "本文")
        save_submission(session, created.id, yuki_id, "回答1")
        save_submission(session, created.id, yuki_id, "回答2")

        rows = (
            session.query(AssignmentSubmission)
            .filter(AssignmentSubmission.assignment_id == created.id)
            .all()
        )

    assert len(rows) == 1
    assert rows[0].answer_text == "回答2"
    assert rows[0].user_id == yuki_id


def test_save_submission_missing_assignment_returns_error(bootstrapped_db, user_ids):
    with db.session_scope() as session:
        result = save_submission(session, 999999, user_ids["yuki"], "回答")

    assert result is SubmissionSaveError.ASSIGNMENT_NOT_FOUND


def test_save_submission_after_reviewed_returns_error(bootstrapped_db, user_ids):
    yuki_id = user_ids["yuki"]
    with db.session_scope() as session:
        created = create_assignment(session, "タイトル", "本文")
        save_submission(session, created.id, yuki_id, "回答")
        save_member_feedback(session, created.id, yuki_id, "コメント")

        result = save_submission(session, created.id, yuki_id, "新しい回答")

    assert result is SubmissionSaveError.ALREADY_REVIEWED


def test_different_users_have_independent_submissions(bootstrapped_db, user_ids):
    yuki_id, sora_id = user_ids["yuki"], user_ids["sora"]
    with db.session_scope() as session:
        created = create_assignment(session, "タイトル", "本文")
        save_submission(session, created.id, yuki_id, "ユウキの回答")

        yuki_detail = get_assignment_detail(created.id, yuki_id, "member")
        sora_detail = get_assignment_detail(created.id, sora_id, "member")

    assert yuki_detail.status == "submitted"
    assert sora_detail.status == "not_submitted"
    assert sora_detail.submission is None


def test_save_member_feedback_missing_assignment_returns_error(bootstrapped_db, user_ids):
    with db.session_scope() as session:
        result = save_member_feedback(session, 999999, user_ids["yuki"], "コメント")

    assert result is FeedbackSaveError.ASSIGNMENT_NOT_FOUND


def test_save_member_feedback_missing_user_returns_error(bootstrapped_db):
    with db.session_scope() as session:
        created = create_assignment(session, "タイトル", "本文")

        result = save_member_feedback(session, created.id, 999999, "コメント")

    assert result is FeedbackSaveError.USER_NOT_FOUND


def test_save_member_feedback_admin_target_returns_error(bootstrapped_db, user_ids):
    with db.session_scope() as session:
        created = create_assignment(session, "タイトル", "本文")

        result = save_member_feedback(session, created.id, user_ids["sensei"], "コメント")

    assert result is FeedbackSaveError.USER_NOT_FOUND


def test_save_member_feedback_without_submission_returns_error(bootstrapped_db, user_ids):
    with db.session_scope() as session:
        created = create_assignment(session, "タイトル", "本文")

        result = save_member_feedback(session, created.id, user_ids["yuki"], "コメント")

    assert result is FeedbackSaveError.NOT_SUBMITTED


def test_fetch_assignment_list_orders_by_created_at_desc(bootstrapped_db, user_ids):
    items = fetch_assignment_list(user_ids["yuki"], "member")

    created_ats = [item.createdAt for item in items]
    assert created_ats == sorted(created_ats, reverse=True)


def test_fetch_assignment_list_same_created_at_tiebreak_by_id_desc(bootstrapped_db, user_ids):
    same_created_at = "2026-09-20T00:00:00+00:00"
    with db.session_scope() as session:
        first = Assignment(title="同時刻1", body="本文1", created_at=same_created_at)
        second = Assignment(title="同時刻2", body="本文2", created_at=same_created_at)
        session.add(first)
        session.add(second)
        session.commit()
        first_id, second_id = first.id, second.id

    items = fetch_assignment_list(user_ids["yuki"], "member")
    tied_ids = [item.id for item in items if item.createdAt == same_created_at]

    assert tied_ids == sorted([first_id, second_id], reverse=True)


def test_fetch_assignment_list_status_is_not_submitted_for_user_without_submission(
    bootstrapped_db, user_ids
):
    items = fetch_assignment_list(user_ids["sensei"], "admin")

    assert all(item.status == "not_submitted" for item in items)


def test_get_assignment_detail_returns_none_when_missing(bootstrapped_db, user_ids):
    assert get_assignment_detail(999999, user_ids["yuki"], "member") is None


def test_fetch_member_submissions_includes_not_submitted_members_sorted_by_name(
    bootstrapped_db, user_ids
):
    with db.session_scope() as session:
        created = create_assignment(session, "タイトル", "本文")
        save_submission(session, created.id, user_ids["yuki"], "ユウキの回答")

        submissions = fetch_member_submissions(session, created.id)

    assert [item.user.displayName for item in submissions] == ["ソラ", "ハルカ", "ユウキ"]
    statuses = {item.user.displayName: item.status for item in submissions}
    assert statuses == {"ソラ": "not_submitted", "ハルカ": "not_submitted", "ユウキ": "submitted"}


def test_fetch_member_submissions_missing_assignment_returns_none(bootstrapped_db):
    with db.session_scope() as session:
        assert fetch_member_submissions(session, 999999) is None
