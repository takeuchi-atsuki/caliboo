"""DBエンジン初期化・セッション管理・シード投入。

!NOTE: engineはモジュールレベルでは生成しない。`init_engine()`を明示的に呼び出した
       タイミングでのみ生成することで、テストごとに異なるDBパスへ確実に切り替えられる
       ようにしている(モジュールロード時に生成すると、テストの度にDBパスを切り替えられない)。
"""

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, Iterator

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from caliboo_api.auth.password import hash_password
from caliboo_api.data.account_data import initialize_extensions
from caliboo_api.data.seed import (
    assignment_seed,
    home_seed,
    ojt_seed,
    report_seed,
    study_seed,
    user_seed,
)
from caliboo_api.models import (
    Assignment,
    AssignmentSubmission,
    Base,
    Certification,
    Department,
    DepartmentMessage,
    HomeProfile,
    KnowledgeItem,
    ProgressCategory,
    QuizQuestion,
    RelatedQuestion,
    Report,
    User,
)

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def init_engine(path: str) -> None:
    """SQLite用のengine/sessionmakerを生成し、グローバルに設定する。

    渡された`path`の親ディレクトリが存在しない場合は自動作成する。
    """
    global _engine, _SessionLocal

    parent_dir = os.path.dirname(os.path.abspath(path))
    if parent_dir and not os.path.isdir(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    _engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    """現在設定されているengineからセッションを取得する(FastAPIの`Depends`で使う想定)。"""
    if _SessionLocal is None:
        raise RuntimeError("engine is not initialized. call init_engine() first.")

    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """`get_session()`をデータ層の関数から手動利用するためのラッパー。

    後始末(`session.close()`)は`get_session()`側の実装に一本化するため、
    ここではジェネレータを手動で駆動するだけに留める。
    """
    generator = get_session()
    session = next(generator)
    try:
        yield session
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


def _seed_users(session: Session) -> dict[str, User]:
    """開発用ユーザーを投入する。パスワードは`hash_password()`でハッシュ化してから保存する。"""
    users: dict[str, User] = {}
    for entry in user_seed.USERS_SEED:
        user = User(
            login_id=entry["login_id"],
            display_name=entry["display_name"],
            role=entry["role"],
            password_hash=hash_password(entry["password"]),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        session.add(user)
        session.flush()
        users[entry["login_id"]] = user
    return users


def _seed_home(session: Session, users: dict[str, User]) -> None:
    """ユーザーごとにcertification行→home_profile行の順で投入する(不変条件: 全ユーザーが
    home_profileを1行持つ)。"""
    for login_id, profile_seed in home_seed.HOME_PROFILES_SEED.items():
        certification = Certification(
            name=profile_seed["certification_name"],
            achievement_percent=profile_seed["achievement_percent"],
        )
        session.add(certification)
        session.flush()

        session.add(
            HomeProfile(
                user_id=users[login_id].id,
                user_streak_days=profile_seed["user_streak_days"],
                strength1_label=profile_seed["strength1_label"],
                strength1_tone=profile_seed["strength1_tone"],
                strength2_label=profile_seed["strength2_label"],
                strength2_tone=profile_seed["strength2_tone"],
                strength3_label=profile_seed["strength3_label"],
                strength3_tone=profile_seed["strength3_tone"],
                certification_id=certification.id,
            )
        )


def _seed_ojt(session: Session) -> None:
    for dept in ojt_seed.DEPARTMENTS_SEED:
        session.add(
            Department(
                id=dept["id"],
                name=dept["name"],
                icon=dept["icon"],
                color=dept["color"],
                knowledge_count=dept["knowledge_count"],
            )
        )

    for dept_id, messages in ojt_seed.INITIAL_MESSAGES_SEED.items():
        for ordinal, message in enumerate(messages, start=1):
            session.add(
                DepartmentMessage(
                    department_id=dept_id,
                    role=message["role"],
                    text=message["text"],
                    ordinal=ordinal,
                )
            )

    for dept_id, items in ojt_seed.KNOWLEDGE_SEED.items():
        for item in items:
            session.add(
                KnowledgeItem(
                    department_id=dept_id,
                    title=item["title"],
                    description=item["description"],
                )
            )


def _seed_study(session: Session) -> None:
    for question in study_seed.QUIZ_QUESTIONS_SEED:
        session.add(
            QuizQuestion(
                id=question["id"],
                category=question["category"],
                text=question["text"],
                choices=question["choices"],
                correct_index=question["correct_index"],
                explanation=question["explanation"],
                time_limit_sec=question["time_limit_sec"],
                source=question.get("source"),
            )
        )

    for category in study_seed.PROGRESS_CATEGORIES_SEED:
        session.add(
            ProgressCategory(
                id=category["id"],
                label=category["label"],
                percent=category["percent"],
            )
        )

    for item in study_seed.RELATED_QUESTIONS_SEED:
        session.add(
            RelatedQuestion(
                id=item["id"],
                title=item["title"],
                question_count=item["question_count"],
                tags=item["tags"],
            )
        )


def _seed_assignment(session: Session, users: dict[str, User]) -> None:
    """課題提出シードは`yuki`に紐づける(契約: yukiが既存の提出(reviewed/submitted)を引き継ぐ)。"""
    assignment_ids: list[int] = []
    for assignment in assignment_seed.ASSIGNMENTS_SEED:
        row = Assignment(
            title=assignment["title"],
            body=assignment["body"],
            created_at=assignment["created_at"],
        )
        session.add(row)
        session.flush()
        assignment_ids.append(row.id)

    submitter_id = users["yuki"].id
    for submission in assignment_seed.ASSIGNMENT_SUBMISSIONS_SEED:
        session.add(
            AssignmentSubmission(
                assignment_id=assignment_ids[submission["assignment_index"]],
                user_id=submitter_id,
                answer_text=submission["answer_text"],
                submitted_at=submission["submitted_at"],
                feedback_comment=submission["feedback_comment"],
                feedback_at=submission["feedback_at"],
            )
        )


def _seed_report(session: Session, users: dict[str, User]) -> None:
    """日報(KPT)シードを投入する(現状は`haruka`のみ。`report_seed.REPORTS_SEED`参照)。"""
    for login_id, reports in report_seed.REPORTS_SEED.items():
        user = users[login_id]
        for report in reports:
            session.add(
                Report(
                    user_id=user.id,
                    date=report["date"],
                    keep=report["keep"],
                    problem=report["problem"],
                    try_=report["try"],
                    mood=report["mood"],
                    mood_comment=report["mood_comment"],
                    status="submitted",
                    saved_at=f"{report['date']}T18:00:00+00:00",
                )
            )


def _demo_seed_enabled() -> bool:
    return os.environ.get("CALIBOO_DEMO_SEED", "true").strip().lower() in {"1", "true"}


def _check_schema_compatibility(session: Session) -> None:
    """旧スキーマ(`users`テーブル導入前)のDBを検知し、起動を失敗させる。

    !NOTE: マイグレーションを用意していないため、旧DBを検出した
           場合は削除して作り直してもらう。`Base.metadata.create_all()`は既存テーブルの
           列を追加・変更しないため、旧`home_profile`(`user_id`列が無い)はそのまま
           残ってしまう。「`departments`は既にシード済み(=旧DBとして稼働していた)なのに
           `users`が空、または`home_profile`に`user_id`列が無い」を旧スキーマの目印にする。
    """
    if _engine is None:
        return
    inspector = inspect(_engine)
    if "home_profile" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("home_profile")}
    departments_seeded = session.query(Department).first() is not None
    users_seeded = session.query(User).first() is not None

    if departments_seeded and (
        (not users_seeded and _demo_seed_enabled()) or "user_id" not in columns
    ):
        raise RuntimeError(
            "旧スキーマのDBを検出しました。backend/var/caliboo.db を削除して再起動してください。"
        )


def bootstrap_db() -> None:
    """テーブル作成＋(初回のみ)シード投入を行う。

    !NOTE: シード投入の要否は「ファイルが新規作成されたか」ではなく「`departments`
           テーブルが空かどうか」で判定する。テスト用の一時DBファイルは事前に
           空ファイルとして存在してしまうことがあり、ファイル存在判定では機能しないため。

    !NOTE: シードはユーザー→資格→home_profileの順に投入する(`_seed_home`が各ユーザーに
           ひも付くcertification行を先に作ってからhome_profile行を作るため)。
    """
    if _engine is None or _SessionLocal is None:
        raise RuntimeError("engine is not initialized. call init_engine() first.")

    Base.metadata.create_all(_engine)

    with session_scope() as session:
        _check_schema_compatibility(session)

        if session.query(Department).first() is not None:
            initialize_extensions(session)
            return

        if _demo_seed_enabled():
            users = _seed_users(session)
            _seed_home(session, users)
            _seed_assignment(session, users)
            _seed_report(session, users)
        _seed_ojt(session)
        _seed_study(session)
        session.commit()
        initialize_extensions(session)
