from caliboo_api.data.seed.assignment_seed import (
    ASSIGNMENT_SUBMISSIONS_SEED,
    ASSIGNMENTS_SEED,
)


def test_assignment_titles_are_unique():
    titles = [assignment["title"] for assignment in ASSIGNMENTS_SEED]

    assert len(titles) == len(set(titles))


def test_every_assignment_has_non_empty_title_and_body():
    for assignment in ASSIGNMENTS_SEED:
        assert assignment["title"].strip()
        assert assignment["body"].strip()


def test_submission_assignment_index_within_range():
    for submission in ASSIGNMENT_SUBMISSIONS_SEED:
        assert 0 <= submission["assignment_index"] < len(ASSIGNMENTS_SEED)


def test_submission_assignment_index_has_no_duplicates():
    indexes = [submission["assignment_index"] for submission in ASSIGNMENT_SUBMISSIONS_SEED]

    assert len(indexes) == len(set(indexes))


def test_feedback_comment_and_feedback_at_are_consistent():
    for submission in ASSIGNMENT_SUBMISSIONS_SEED:
        has_comment = submission["feedback_comment"] is not None
        has_feedback_at = submission["feedback_at"] is not None
        assert has_comment == has_feedback_at


def test_seed_covers_all_three_states():
    reviewed_indexes = {
        submission["assignment_index"]
        for submission in ASSIGNMENT_SUBMISSIONS_SEED
        if submission["feedback_comment"] is not None
    }
    submitted_indexes = {
        submission["assignment_index"]
        for submission in ASSIGNMENT_SUBMISSIONS_SEED
        if submission["feedback_comment"] is None
    }
    submitted_or_reviewed = {
        submission["assignment_index"] for submission in ASSIGNMENT_SUBMISSIONS_SEED
    }
    not_submitted_indexes = set(range(len(ASSIGNMENTS_SEED))) - submitted_or_reviewed

    assert reviewed_indexes
    assert submitted_indexes
    assert not_submitted_indexes
