from sqlalchemy import UniqueConstraint

from caliboo_api.models import (
    AssignmentSubmission,
    Base,
    HomeProfile,
    Report,
    User,
    UserSession,
)


def test_base_metadata_contains_all_expected_tables():
    expected_tables = {
        "users",
        "user_sessions",
        "certifications",
        "home_profile",
        "departments",
        "department_messages",
        "knowledge_items",
        "quiz_questions",
        "progress_categories",
        "related_questions",
        "reports",
        "assignments",
        "assignment_submissions",
    }

    assert expected_tables.issubset(set(Base.metadata.tables.keys()))


def test_report_try_column_physical_name_is_try():
    column = Report.__table__.c["try"]

    assert column.name == "try"


def test_report_try_attribute_maps_to_try_column():
    report = Report(
        user_id=1,
        date="2026-07-15",
        keep="keep",
        problem="problem",
        try_="try-value",
        mood=["fun", "tired"],
        mood_comment="",
        status="draft",
        saved_at="2026-07-15T00:00:00+00:00",
    )

    assert report.try_ == "try-value"


def test_report_has_not_null_user_id_column():
    column = Report.__table__.c["user_id"]

    assert column.nullable is False


def test_user_login_id_and_external_id_are_unique_and_password_hash_is_nullable():
    columns = {column.name: column for column in User.__table__.columns}

    assert columns["login_id"].unique
    assert columns["login_id"].nullable is False
    assert columns["external_id"].unique
    assert columns["external_id"].nullable is True
    assert columns["password_hash"].nullable is True
    assert columns["role"].nullable is False


def test_user_session_primary_key_is_token_hash():
    assert [column.name for column in UserSession.__table__.primary_key.columns] == [
        "token_hash"
    ]


def test_home_profile_no_longer_has_user_name_or_hero_message_columns():
    columns = {column.name for column in HomeProfile.__table__.columns}

    assert "user_name" not in columns
    assert "hero_message" not in columns
    assert "user_id" in columns


def test_home_profile_user_id_and_certification_id_are_unique():
    unique_columns = {column.name for column in HomeProfile.__table__.columns if column.unique}

    assert {"user_id", "certification_id"} <= unique_columns


def test_assignment_submission_unique_constraint_is_assignment_and_user():
    constraint = next(
        constraint
        for constraint in AssignmentSubmission.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    )

    assert {column.name for column in constraint.columns} == {"assignment_id", "user_id"}


def test_assignment_submission_has_not_null_user_id_column():
    column = AssignmentSubmission.__table__.c["user_id"]

    assert column.nullable is False
