import sqlite3

import caliboo_api.db as db
from caliboo_api.data.assignment_proposal_data import create_or_get_pending_proposal
from caliboo_api.data.seed.user_seed import USERS_SEED
from caliboo_api.models import AssignmentSubmission, Department, HomeProfile, User


def test_bootstrap_db_seeds_data_on_first_call(tmp_path):
    db_path = str(tmp_path / "seed_once.db")
    db.init_engine(db_path)

    db.bootstrap_db()

    with db.session_scope() as session:
        assert session.query(Department).count() == 6


def test_bootstrap_db_does_not_reseed_on_second_call(tmp_path):
    db_path = str(tmp_path / "seed_twice.db")
    db.init_engine(db_path)

    db.bootstrap_db()
    db.bootstrap_db()

    with db.session_scope() as session:
        assert session.query(Department).count() == 6


def test_bootstrap_db_seeds_users_with_hashed_passwords(tmp_path):
    db_path = str(tmp_path / "seed_users.db")
    db.init_engine(db_path)

    db.bootstrap_db()

    with db.session_scope() as session:
        users_by_login_id = {user.login_id: user for user in session.query(User).all()}

    assert set(users_by_login_id) == {seed["login_id"] for seed in USERS_SEED}
    for seed in USERS_SEED:
        user = users_by_login_id[seed["login_id"]]
        assert user.role == seed["role"]
        assert user.display_name == seed["display_name"]
        assert user.password_hash != seed["password"]
        assert user.password_hash.startswith("scrypt$")


def test_bootstrap_db_gives_every_user_a_home_profile(tmp_path):
    """不変条件: 全ユーザーがhome_profileを1行持つ。"""
    db_path = str(tmp_path / "seed_home_profiles.db")
    db.init_engine(db_path)

    db.bootstrap_db()

    with db.session_scope() as session:
        user_count = session.query(User).count()
        profile_count = session.query(HomeProfile).count()

    assert user_count == 4
    assert profile_count == 4


def test_bootstrap_db_assigns_seeded_assignment_submissions_to_yuki(tmp_path):
    db_path = str(tmp_path / "seed_submissions.db")
    db.init_engine(db_path)

    db.bootstrap_db()

    with db.session_scope() as session:
        yuki = session.query(User).filter(User.login_id == "yuki").first()
        submission_user_ids = {
            row.user_id for row in session.query(AssignmentSubmission).all()
        }

    assert submission_user_ids == {yuki.id}


def test_bootstrap_db_creates_new_tables_for_pre_17_database_and_proposal_api_works(tmp_path):
    """#17より前(assignment_proposals/assignment_recipients未導入)のDBを想定し、
    再起動で新テーブルだけが追加され、`_check_schema_compatibility`が誤検知しないことを
    確認する(新テーブルは`create_all()`が既存DBにも作成できるため、旧スキーマ検出とは
    無関係)。日報シードを持つ新入社員ハルカが存在し、新テーブル追加後も課題案生成が
    動作することも合わせて確認する。
    """
    db_path = str(tmp_path / "pre_17.db")
    db.init_engine(db_path)
    db.bootstrap_db()

    connection = sqlite3.connect(db_path)
    connection.execute("DROP TABLE assignment_proposals")
    connection.execute("DROP TABLE assignment_recipients")
    connection.commit()
    connection.close()

    db.bootstrap_db()

    inspector = sqlite3.connect(db_path)
    table_names = {
        row[0]
        for row in inspector.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    inspector.close()
    assert {"assignment_proposals", "assignment_recipients"} <= table_names

    with db.session_scope() as session:
        haruka = session.query(User).filter(User.login_id == "haruka").first()
        assert haruka is not None
        haruka_id = haruka.id

    result = create_or_get_pending_proposal(haruka_id)
    detail, is_new = result
    assert is_new is True
    assert detail.status == "pending"
