from caliboo_api.data.study_data import (
    fetch_related_questions,
    fetch_study_progress,
    get_question,
    list_questions,
)


def test_fetch_study_progress(bootstrapped_db, user_ids):
    progress = fetch_study_progress(user_ids["yuki"])

    assert progress.certification.name == "基本情報技術者"
    assert progress.certification.achievementPercent == 68
    assert len(progress.categories) == 3
    assert progress.streakDays == 12


def test_fetch_study_progress_is_isolated_per_user(bootstrapped_db, user_ids):
    progress = fetch_study_progress(user_ids["sora"])

    assert progress.certification.achievementPercent == 20
    assert progress.streakDays == 3


def test_fetch_related_questions(bootstrapped_db):
    items = fetch_related_questions()

    assert len(items) == 3


def test_list_questions_without_category(bootstrapped_db):
    records = list_questions(None)

    assert len(records) == 24
    assert records[0].id == "q_101"


def test_list_questions_with_category(bootstrapped_db):
    records = list_questions("management")

    assert len(records) == 6
    assert all(record.category == "management" for record in records)


def test_get_question_found(bootstrapped_db):
    record = get_question("q_101")

    assert record is not None
    assert record.correct_index == 1
    assert record.explanation

    question = record.to_public_question()
    assert question.id == "q_101"
    assert question.category == "technology"
    assert question.source is None


def test_get_question_with_source_is_propagated_to_public_question(bootstrapped_db):
    record = get_question("q_103")

    assert record is not None
    assert record.source == "令和8年度 基本情報技術者試験 科目A 問1"

    question = record.to_public_question()
    assert question.source == "令和8年度 基本情報技術者試験 科目A 問1"


def test_get_question_not_found(bootstrapped_db):
    assert get_question("unknown") is None
