from caliboo_api.data.ojt_data import (
    fetch_departments,
    get_department,
    get_initial_messages,
    get_knowledge,
)


def test_fetch_departments(bootstrapped_db):
    departments = fetch_departments()

    assert len(departments) == 6
    assert {d.id for d in departments} == {"dev", "qa", "sales", "design", "mfg", "ga"}


def test_get_department_found(bootstrapped_db):
    dept = get_department("dev")

    assert dept is not None
    assert dept.name == "開発課"


def test_get_department_not_found(bootstrapped_db):
    assert get_department("unknown") is None


def test_get_initial_messages_found(bootstrapped_db):
    messages = get_initial_messages("dev")

    assert messages is not None
    assert len(messages) == 1
    assert messages[0].id == "dev-m1"
    assert messages[0].role == "bot"


def test_get_initial_messages_not_found(bootstrapped_db):
    assert get_initial_messages("unknown") is None


def test_get_knowledge_found(bootstrapped_db):
    items = get_knowledge("dev")

    assert items is not None
    assert len(items) == 3
    assert items[0].id == "k1"


def test_get_knowledge_not_found(bootstrapped_db):
    assert get_knowledge("unknown") is None
