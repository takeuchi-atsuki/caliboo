from caliboo_api.data.seed.study_seed import QUIZ_QUESTIONS_SEED


def test_question_ids_are_unique():
    ids = [question["id"] for question in QUIZ_QUESTIONS_SEED]

    assert len(ids) == len(set(ids))


def test_correct_index_is_within_choices_range():
    for question in QUIZ_QUESTIONS_SEED:
        assert 0 <= question["correct_index"] < len(question["choices"])


def test_choices_have_exactly_four_options():
    for question in QUIZ_QUESTIONS_SEED:
        assert len(question["choices"]) == 4


def test_every_question_has_non_empty_text_and_explanation():
    for question in QUIZ_QUESTIONS_SEED:
        assert question["text"].strip()
        assert question["explanation"].strip()
