"""共有DBの設定・方言・スナップショット検証(外部接続なし)。"""

import secrets
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
from sqlalchemy import create_engine, event, inspect, insert, null, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import URL
from sqlalchemy.schema import CreateIndex

from caliboo_api import db
from caliboo_api.config import get_settings, parse_database_url
from caliboo_api.dialect import conflict_insert, lock_attempt_source, lock_user
from caliboo_api.migration import (
    _copy_table, _fingerprint, _sequence_floors, snapshot_connection, snapshot_sqlite,
)
from caliboo_api.models import AssignmentProposal, Base, Report, User


def test_explicit_url_selects_psycopg_and_never_uses_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("CALIBOO_DATABASE_URL", "postgresql://synthetic@localhost/caliboo_test")
    monkeypatch.setenv("CALIBOO_SQLITE_PATH", str(tmp_path / "absent.db"))
    settings = get_settings()
    assert settings.database_url == URL.create(
        "postgresql+psycopg", username="synthetic", host="localhost", database="caliboo_test",
    )
    engine = Mock()
    monkeypatch.setattr(db, "shared_engine", lambda url: engine)
    monkeypatch.setattr(db, "_set_engine", lambda actual: None)
    db.configure_engine(settings)
    assert not (tmp_path / "absent.db").exists()


@pytest.mark.parametrize("value", ["", "invalid", "sqlite:///file.db", "postgresql://localhost"])
def test_invalid_explicit_url_is_error(monkeypatch, value):
    monkeypatch.setenv("CALIBOO_DATABASE_URL", value)
    with pytest.raises(ValueError, match="CALIBOO_DATABASE_URL"):
        get_settings()


def test_conflict_insert_is_compiled_for_the_actual_dialect():
    for dialect in (sqlite.dialect(), postgresql.dialect()):
        session = Mock()
        session.get_bind.return_value.dialect = dialect
        statement = conflict_insert(session, User).values(
            login_id="example").on_conflict_do_nothing(index_elements=[User.login_id])
        assert "ON CONFLICT" in str(statement.compile(dialect=dialect))
    session.get_bind.return_value.dialect.name = "other"
    with pytest.raises(RuntimeError, match="unsupported"):
        conflict_insert(session, User)


def test_pg_pending_index_is_partial_and_sqlite_unchanged():
    index = next(index for index in AssignmentProposal.__table__.indexes
                 if index.name == "uq_assignment_proposals_pending_user")
    ddl = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert "CREATE UNIQUE INDEX" in ddl
    assert "WHERE assignment_id IS NULL AND decided_at IS NULL" in ddl
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    names = {i["name"] for i in inspect(engine).get_indexes("assignment_proposals")}
    assert index.name not in names


@pytest.mark.parametrize("inserted_id, expected_new", [(42, True), (None, False)])
def test_pg_proposal_creation_uses_returning_not_rowcount(monkeypatch, inserted_id, expected_new):
    from caliboo_api.data import assignment_proposal_data as data

    session = Mock()
    session.get_bind.return_value.dialect = postgresql.dialect()
    # PostgreSQLのINSERT件数を取得できない場合も、新規/既存の判定を誤らない。
    result = session.execute.return_value
    result.rowcount = -1
    result.scalar_one_or_none.return_value = inserted_id
    pending = AssignmentProposal(id=42, target_user_id=123)
    monkeypatch.setattr(data, "_find_pending_proposal", Mock(return_value=pending))
    output = dict(title="合成案", body="合成課題本文", messageForMember="",
                  aim="確認", rationale="合成理由", estimateMinutes=10,
                  materials=[], progress={}, themeKey="synthetic")

    proposal, is_new = data.save_generated_proposal(session, 123, output, "manual")

    assert proposal is pending
    assert is_new is expected_new
    result.scalar_one_or_none.assert_called_once()
    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT" in sql
    assert "DO NOTHING RETURNING assignment_proposals.id" in sql
    data._find_pending_proposal.assert_called_once_with(session, 123)


def test_lock_business_mutation_uses_pg_transaction_scoped_lock():
    session = Mock()
    session.get_bind.return_value.dialect = postgresql.dialect()
    lock_user(session, 123)
    query = session.query.return_value.filter_by.return_value.populate_existing.return_value
    query.with_for_update.assert_called_once_with(key_share=True)
    lock_attempt_source(session, "synthetic", reset=True)
    assert session.execute.call_args.args[1] == {"key": "reset:synthetic"}
    session.reset_mock()
    session.get_bind.return_value.dialect = sqlite.dialect()
    lock_user(session, 123)
    lock_attempt_source(session, "synthetic")
    session.query.assert_not_called()
    session.execute.assert_not_called()


def test_snapshot_copies_all_tables_and_preserves_content_and_sequence(bootstrapped_db, tmp_path):
    # 同じ日報の明示SQL NULLとJSON nullを区別して移行する。
    with db.get_engine().begin() as source:
        user_id = source.execute(select(User.id).limit(1)).scalar_one()
        values = dict(user_id=user_id, date="2026-01-01", keep="合成日報", problem="",
                      try_="", mood_comment="", status="draft",
                      saved_at="2026-01-01T00:00:00+00:00")
        values["try"] = values.pop("try_")
        for value in [null(), Report.__table__.c.mood.type.NULL, ["fun"]]:
            source.execute(insert(Report.__table__).values(**values, mood=value))
        source.execute(insert(Report.__table__).values(**values, mood=[], id=12345))
        source.execute(Report.__table__.delete().where(Report.id == 12345))
    snapshot = tmp_path / "snapshot.db"
    snapshot_sqlite(Path(bootstrapped_db), snapshot)
    with pytest.raises(FileExistsError):
        snapshot_sqlite(Path(bootstrapped_db), snapshot)
    copy = create_engine("sqlite://")
    Base.metadata.create_all(copy)
    with snapshot_connection(snapshot) as source, copy.begin() as target:
        for table in Base.metadata.sorted_tables:
            _copy_table(source, target, table)
            assert _fingerprint(source, table) == _fingerprint(target, table)
        floors = {table.name: floor for table, _, floor in _sequence_floors(source)}
        assert floors["reports"] == 12345
        assert len(inspect(source).get_table_names()) == 40


def test_snapshot_rejects_unknown_schema(tmp_path):
    path = tmp_path / "incomplete.db"
    with sqlite3.connect(path):
        pass
    with pytest.raises(RuntimeError, match="テーブル構成"):
        with snapshot_connection(path):
            pass


def test_shared_startup_requires_initialized_schema(monkeypatch):
    settings = get_settings()
    settings.database_url = parse_database_url("postgresql://localhost/caliboo_test")
    engine = create_engine("sqlite://")
    monkeypatch.setattr(db, "shared_engine", lambda url: engine)
    with pytest.raises(RuntimeError, match="未初期化"):
        db.prepare_runtime(settings)


def test_shared_engine_constructs_psycopg_pool_without_connecting(monkeypatch):
    creator = Mock()
    monkeypatch.setattr(db, "create_engine", creator)
    url = parse_database_url("postgresql://localhost/caliboo_test")
    assert db.shared_engine(url) is creator.return_value
    creator.assert_called_once_with(
        url, pool_pre_ping=True, hide_parameters=True, connect_args={"connect_timeout": 5})


def test_runtime_unavailable_does_not_fallback(monkeypatch):
    from sqlalchemy.exc import OperationalError

    settings = get_settings()
    settings.database_url = parse_database_url("postgresql://localhost/caliboo_test")
    engine = Mock()
    engine.connect.side_effect = OperationalError(None, None, RuntimeError("synthetic failure"))
    monkeypatch.setattr(db, "shared_engine", lambda url: engine)
    with pytest.raises(RuntimeError, match="共有DBに接続できません"):
        db.prepare_runtime(settings)


def test_shared_schema_checks_columns_and_pending_index():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        db.require_empty_shared_db(connection)
        Base.metadata.create_all(connection)
        with pytest.raises(RuntimeError, match="空ではありません"):
            db.require_empty_shared_db(connection)
        with pytest.raises(RuntimeError, match="一意制約"):
            db.validate_shared_schema(connection)
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_assignment_proposals_pending_user ON assignment_proposals"
            "(target_user_id) WHERE assignment_id IS NULL AND decided_at IS NULL")
        db.validate_shared_schema(connection)
        connection.exec_driver_sql("ALTER TABLE users ADD COLUMN obsolete VARCHAR")
        with pytest.raises(RuntimeError, match="スキーマが異なります"):
            db.validate_shared_schema(connection)
    db.lock_shared_initialization(Mock())


@pytest.mark.parametrize("demo,expected", [(False, 0), (True, 4)])
def test_independent_initialization_never_uses_automatic_seed_setting(
        monkeypatch, tmp_path, demo, expected):
    # PG固有の排他・DDL部分は独立して検査。ここでは初期化トランザクションとシードを検証。
    engine = create_engine(URL.create("sqlite", database=str(tmp_path / "target.db")))
    event.listen(engine, "connect", lambda conn, record: conn.execute("PRAGMA foreign_keys=ON"))
    monkeypatch.setattr(db, "shared_engine", lambda url: engine)
    monkeypatch.setattr(db, "lock_shared_initialization", Mock())
    monkeypatch.setattr(db, "validate_shared_schema", Mock())
    monkeypatch.setenv("CALIBOO_DEMO_SEED", "false" if demo else "true")
    url = parse_database_url("postgresql://localhost/caliboo_test")
    db.initialize_shared_db(url, demo=demo)
    with engine.connect() as connection:
        assert len(inspect(connection).get_table_names()) == 40
        assert len(connection.execute(select(User.id)).all()) == expected
    with pytest.raises(RuntimeError, match="空ではありません"):
        db.initialize_shared_db(url, demo=demo)


def test_sequence_floor_calls_and_verification(bootstrapped_db):
    from caliboo_api import migration

    with snapshot_connection(Path(bootstrapped_db)) as source:
        target = Mock()
        target.execute.return_value.scalar_one.return_value = "test_sequence"
        migration._set_sequences(source, target)
        assert any(call.args[1].get("called") is True
                   for call in target.execute.call_args_list)
        assert any(call.args[1].get("called") is False
                   for call in target.execute.call_args_list)
        target.execute.return_value.scalar_one.side_effect = [None]
        first_table = next(iter(Base.metadata.sorted_tables))
        with pytest.raises(RuntimeError, match="採番シーケンス"):
            migration._sequence_name(target, first_table, first_table.c[0])
        target.execute.return_value.scalar_one.side_effect = None
        monkey = Mock(return_value="test_sequence")
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(migration, "_sequence_name", monkey)
            target.execute.return_value.scalar_one.return_value = 999999
            migration._verify_sequences(source, target)
            target.execute.return_value.scalar_one.return_value = 0
            with pytest.raises(RuntimeError, match="採番シーケンスが一致しません"):
                migration._verify_sequences(source, target)


def test_migration_transaction_and_content_mismatch(bootstrapped_db, tmp_path, monkeypatch):
    from caliboo_api import migration

    target = create_engine(URL.create("sqlite", database=str(tmp_path / "target.db")))
    event.listen(target, "connect", lambda conn, record: conn.execute("PRAGMA foreign_keys=ON"))
    # PG固有の採番・初期化ロックを単体で置換し、全表コピー処理を同じ経路で実行。
    monkeypatch.setattr(migration, "shared_engine", lambda url: target)
    monkeypatch.setattr(migration, "lock_shared_initialization", Mock())
    monkeypatch.setattr(migration, "validate_shared_schema", Mock())
    monkeypatch.setattr(migration, "_set_sequences", Mock())
    monkeypatch.setattr(migration, "_verify_sequences", Mock())
    url = parse_database_url("postgresql://localhost/caliboo_test")
    snapshot = Path(bootstrapped_db)
    counts = migration.migrate_sqlite(snapshot, url)
    assert len(counts) == 40 and counts["users"] == 4
    with pytest.raises(RuntimeError, match="空ではありません"):
        migration.migrate_sqlite(snapshot, url)
    with target.begin() as connection:
        connection.execute(User.__table__.update().values(display_name="別の合成名"))
        with snapshot_connection(snapshot) as source:
            with pytest.raises(RuntimeError, match="内容が一致しません"):
                migration._verify(source, connection)


def test_verify_uses_read_only_repeatable_read(monkeypatch, tmp_path):
    from caliboo_api import migration

    engine = Mock()
    engine.connect.return_value = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    target = connection.execution_options.return_value
    from contextlib import nullcontext
    target.begin.return_value = nullcontext()
    monkeypatch.setattr(migration, "shared_engine", lambda url: engine)
    monkeypatch.setattr(migration, "snapshot_connection", lambda path: nullcontext("snapshot"))
    verification = Mock(return_value={"users": 4})
    monkeypatch.setattr(migration, "_verify", verification)
    result = migration.verify_migration(
        tmp_path / "snapshot.db", parse_database_url("postgresql://localhost/caliboo_test"))
    assert result == {"users": 4}
    connection.execution_options.assert_called_once_with(isolation_level="REPEATABLE READ")
    verification.assert_called_once_with("snapshot", target)
    engine.dispose.assert_called_once()


def test_database_cli_dispatches_and_does_not_print_connection_details(
        monkeypatch, tmp_path, capsys):
    from caliboo_api import db_admin
    from sqlalchemy.exc import OperationalError

    url = "postgresql://localhost/caliboo_test"
    monkeypatch.setenv("CALIBOO_DATABASE_URL", url)
    snapshot = tmp_path / "snapshot.db"
    monkeypatch.setattr(db_admin, "snapshot_sqlite", Mock())
    monkeypatch.setattr("sys.argv", ["db_admin", "snapshot", "--source", str(tmp_path / "db"),
                                     "--output", str(snapshot)])
    db_admin.main()
    db_admin.snapshot_sqlite.assert_called_once_with(tmp_path / "db", snapshot)
    monkeypatch.setattr(db_admin, "initialize_shared_db", Mock())
    monkeypatch.setattr("sys.argv", ["db_admin", "init", "--demo"])
    db_admin.main()
    db_admin.initialize_shared_db.assert_called_once_with(parse_database_url(url), demo=True)
    for name, attribute in [("migrate", "migrate_sqlite"), ("verify", "verify_migration")]:
        operation = Mock(return_value={"users": 4})
        monkeypatch.setattr(db_admin, attribute, operation)
        monkeypatch.setattr("sys.argv", ["db_admin", name, "--snapshot", str(snapshot)])
        db_admin.main()
        operation.assert_called_once_with(snapshot, parse_database_url(url))
        assert "検証成功" in capsys.readouterr().out
    marker = secrets.token_hex(16)
    operation.side_effect = OperationalError(None, None, RuntimeError(marker))
    with pytest.raises(SystemExit):
        db_admin.main()
    captured = capsys.readouterr()
    assert marker not in captured.err
    monkeypatch.delenv("CALIBOO_DATABASE_URL")
    with pytest.raises(SystemExit):
        db_admin.main()


def test_database_outage_api_handler_returns_503():
    import asyncio
    from caliboo_api.main import database_unavailable

    marker = secrets.token_hex(16)
    response = asyncio.run(database_unavailable(None, RuntimeError(marker)))
    assert response.status_code == 503
    assert marker.encode() not in response.body
