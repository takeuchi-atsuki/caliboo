"""AIの課題案データ層(data/assignment_proposal_data.py)の実装テスト。

対象者の絞り込み(下書き・他人の日報・他人の提出/未確定FBを含めない)や、
「直近5件」の窓、除外テーマの導出を、DBに直接データを仕込んで検証する。
"""

from datetime import datetime, timezone

import caliboo_api.db as db
from caliboo_api.data import assignment_proposal_data as target
from caliboo_api.data.assignment_data import fetch_visible_assignment_statuses
from caliboo_api.models import Assignment, AssignmentProposal, AssignmentSubmission, Report


def _add_report(session, user_id, date, status="submitted", problem="特に無い。"):
    session.add(
        Report(
            user_id=user_id,
            date=date,
            keep="特に無い。",
            problem=problem,
            try_="特に無い。",
            mood=[],
            mood_comment="特に無い。",
            status=status,
            saved_at=f"{date}T18:00:00+00:00",
        )
    )


# --- _recent_reports ---


def test_recent_reports_windows_to_five_most_recent(bootstrapped_db, user_ids):
    yuki_id = user_ids["yuki"]
    with db.session_scope() as session:
        for day in range(1, 8):
            _add_report(session, yuki_id, f"2026-09-{day:02d}")
        session.commit()

        reports = target._recent_reports(session, yuki_id)

    assert [report["date"] for report in reports] == [
        "2026-09-07",
        "2026-09-06",
        "2026-09-05",
        "2026-09-04",
        "2026-09-03",
    ]


def test_recent_reports_excludes_drafts(bootstrapped_db, user_ids):
    yuki_id = user_ids["yuki"]
    with db.session_scope() as session:
        _add_report(session, yuki_id, "2026-09-01", status="draft")
        _add_report(session, yuki_id, "2026-09-02", status="submitted")
        session.commit()

        reports = target._recent_reports(session, yuki_id)

    assert [report["date"] for report in reports] == ["2026-09-02"]


def test_recent_reports_excludes_other_users_reports(bootstrapped_db, user_ids):
    yuki_id, sora_id = user_ids["yuki"], user_ids["sora"]
    with db.session_scope() as session:
        _add_report(session, sora_id, "2026-09-01")
        session.commit()

        reports = target._recent_reports(session, yuki_id)

    assert reports == []


# --- _all_feedbacks ---


def test_all_feedbacks_excludes_unconfirmed_submissions(bootstrapped_db, user_ids):
    # haruka(シードでは日報のみ・課題提出は無い)を対象にし、既存シードの提出/FBと
    # 混ざらないようにする(yukiには課題演習シードの確定済みFBが既にある)。
    haruka_id = user_ids["haruka"]
    with db.session_scope() as session:
        assignment = Assignment(title="課題", body="本文", created_at="2026-09-01T00:00:00+00:00")
        session.add(assignment)
        session.flush()
        session.add(
            AssignmentSubmission(
                assignment_id=assignment.id,
                user_id=haruka_id,
                answer_text="回答",
                submitted_at="2026-09-01T00:00:00+00:00",
                feedback_comment=None,
                feedback_at=None,
            )
        )
        session.commit()

        feedbacks = target._all_feedbacks(session, haruka_id)

    assert feedbacks == []


def test_all_feedbacks_excludes_other_users_submissions(bootstrapped_db, user_ids):
    haruka_id, sora_id = user_ids["haruka"], user_ids["sora"]
    with db.session_scope() as session:
        assignment = Assignment(title="課題", body="本文", created_at="2026-09-01T00:00:00+00:00")
        session.add(assignment)
        session.flush()
        session.add(
            AssignmentSubmission(
                assignment_id=assignment.id,
                user_id=sora_id,
                answer_text="回答",
                submitted_at="2026-09-01T00:00:00+00:00",
                feedback_comment="コメント",
                feedback_at="2026-09-02T00:00:00+00:00",
            )
        )
        session.commit()

        feedbacks = target._all_feedbacks(session, haruka_id)

    assert feedbacks == []


def test_all_feedbacks_returns_comment_and_jst_date(bootstrapped_db, user_ids):
    haruka_id = user_ids["haruka"]
    with db.session_scope() as session:
        assignment = Assignment(title="課題", body="本文", created_at="2026-09-01T00:00:00+00:00")
        session.add(assignment)
        session.flush()
        # UTC 15:30 は日本時間(+9h)で翌日0:30になる。
        session.add(
            AssignmentSubmission(
                assignment_id=assignment.id,
                user_id=haruka_id,
                answer_text="回答",
                submitted_at="2026-09-01T00:00:00+00:00",
                feedback_comment="良い回答です",
                feedback_at="2026-09-01T15:30:00+00:00",
            )
        )
        session.commit()

        feedbacks = target._all_feedbacks(session, haruka_id)

    assert feedbacks == [{"date": "2026-09-02", "comment": "良い回答です"}]


# --- _excluded_themes ---


def test_excluded_themes_includes_approved_and_rejected_but_not_pending(
    bootstrapped_db, user_ids
):
    yuki_id = user_ids["yuki"]
    now = datetime.now(timezone.utc).isoformat()
    with db.session_scope() as session:
        assignment = Assignment(title="課題", body="本文", created_at=now)
        session.add(assignment)
        session.flush()

        session.add(
            AssignmentProposal(
                target_user_id=yuki_id,
                title="t",
                body="b",
                message_for_member=None,
                aim="a",
                rationale="r",
                estimate_minutes=10,
                materials=[],
                progress={
                    "submittedCount": 0,
                    "reviewedCount": 0,
                    "notSubmittedCount": 0,
                    "recentMoods": [],
                },
                theme_key="approved_theme",
                generator="rule_based_v1",
                created_at=now,
                assignment_id=assignment.id,
                decided_by=None,
                decided_at=now,
            )
        )
        session.add(
            AssignmentProposal(
                target_user_id=yuki_id,
                title="t",
                body="b",
                message_for_member=None,
                aim="a",
                rationale="r",
                estimate_minutes=10,
                materials=[],
                progress={
                    "submittedCount": 0,
                    "reviewedCount": 0,
                    "notSubmittedCount": 0,
                    "recentMoods": [],
                },
                theme_key="rejected_theme",
                generator="rule_based_v1",
                created_at=now,
                assignment_id=None,
                decided_by=None,
                decided_at=now,
            )
        )
        session.add(
            AssignmentProposal(
                target_user_id=yuki_id,
                title="t",
                body="b",
                message_for_member=None,
                aim="a",
                rationale="r",
                estimate_minutes=10,
                materials=[],
                progress={
                    "submittedCount": 0,
                    "reviewedCount": 0,
                    "notSubmittedCount": 0,
                    "recentMoods": [],
                },
                theme_key="pending_theme",
                generator="rule_based_v1",
                created_at=now,
                assignment_id=None,
                decided_by=None,
                decided_at=None,
            )
        )
        session.commit()

        excluded = target._excluded_themes(session, yuki_id)

    assert excluded == {"approved_theme", "rejected_theme"}


# --- 進捗件数(fetch_visible_assignment_statuses)は他人宛て課題を除く ---


def test_visible_assignment_statuses_excludes_other_members_personal_assignment(
    bootstrapped_db, user_ids
):
    from caliboo_api.models import AssignmentRecipient

    yuki_id, sora_id = user_ids["yuki"], user_ids["sora"]
    with db.session_scope() as session:
        before = len(fetch_visible_assignment_statuses(session, yuki_id))

        personal = Assignment(
            title="ソラ宛て課題", body="本文", created_at="2026-09-01T00:00:00+00:00"
        )
        session.add(personal)
        session.flush()
        session.add(
            AssignmentRecipient(assignment_id=personal.id, user_id=sora_id, message_for_member=None)
        )
        session.commit()

        yuki_statuses = fetch_visible_assignment_statuses(session, yuki_id)
        sora_statuses = fetch_visible_assignment_statuses(session, sora_id)

    assert len(yuki_statuses) == before
    assert len(sora_statuses) == before + 1
