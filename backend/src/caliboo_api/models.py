"""SQLAlchemy宣言的モデル定義。

アプリで使用する全テーブルをこのファイルに集約する。
"""

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """アプリのユーザーアカウント。

    !NOTE: `password_hash`はnullableにしている。将来SSOへ移行した場合、SSO経由の
           ユーザーはパスワードを持たなくなるため。`external_id`も同じくSSO用に
           予約したnullable・UNIQUE列で、現状(パスワード認証のみ)は常にNULL。
    """

    __tablename__ = "users"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    login_id = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    password_hash = Column(String, nullable=True)
    external_id = Column(String, nullable=True, unique=True)
    created_at = Column(String, nullable=False)


class UserSession(Base):
    """ログインセッション。

    !NOTE: 主キーをトークンそのものではなく`token_hash`(sha256)にしている。DBが
           漏えいしても、保存された値から有効なセッションを再現(乗っ取り)できない
           ようにするため(発行・検証・破棄は`auth/session.py`に集約する)。
    """

    __tablename__ = "user_sessions"

    token_hash = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(String, nullable=False)
    expires_at = Column(String, nullable=False)


class Assignment(Base):
    """課題演習の課題(講師が作成する出題本体)。"""

    __tablename__ = "assignments"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


class AssignmentSubmission(Base):
    """課題への提出(テキスト回答)と、それに対する講師フィードバック。

    !NOTE: `status`(未提出/レビュー待ち/フィードバック済み)を列として持たない。
           「提出行の有無」と「feedback_commentがNULLか」から導出できる値を列に
           持たせると、更新のたびに両者を同期させる必要が生じ不整合の余地が生まれるため
           (導出ロジックは`data/assignment_data.py`の`_resolve_status()`に集約する)。

    !NOTE: UNIQUE制約は`(assignment_id, user_id)`。新入社員ごとに提出行が分かれる
           ため、「1課題1提出」ではなく「1課題×1ユーザーにつき1提出」が単位になる。
    """

    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id", "user_id", name="uq_assignment_submissions_assignment_user"
        ),
        {"sqlite_autoincrement": True},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answer_text = Column(String, nullable=False)
    submitted_at = Column(String, nullable=False)
    feedback_comment = Column(String, nullable=True)
    feedback_at = Column(String, nullable=True)


class AssignmentRecipient(Base):
    """課題の配信先(個人宛て指定)。

    !NOTE: 行が無い課題は「全員宛て」を表す(従来どおり)。行があれば`user_id`1人だけに
           配信された課題であることを表す。配信先を専用テーブルに切り出しているのは、
           `assignments`本体を「全員宛て前提」のままにして既存の読み出しコードへの
           影響を抑えつつ、個人宛て配信をあとから追加できるようにするため
           (手動作成課題への配信先指定は現状未対応。BACKLOG.md参照)。
    """

    __tablename__ = "assignment_recipients"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message_for_member = Column(String, nullable=True)


class AssignmentProposal(Base):
    """AIの課題案(BACKLOG #17)。講師が確認・編集して配信、または見送るまでの記録。

    !NOTE: `status`(確認待ち/配信済み/見送り)を列として持たない。`AssignmentSubmission`
           の`_resolve_status()`と同じ方針で、`assignment_id`(配信先課題)が設定されて
           いれば配信済み、無くても`decided_at`(見送り確定日時)が設定されていれば見送り、
           どちらも無ければ確認待ち、と導出する(専用の状態列を持たせると、配信・見送りの
           度に列を同期する必要が生じ不整合の余地が生まれるため)。`rejected_at`という
           専用列も持たない(`decided_at`と`assignment_id`の有無だけで一意に導出できるため)。

    !NOTE: 生成時点の内容(`title`/`body`/`message_for_member`)は配信後も変更しない。
           配信内容は`Assignment`/`AssignmentRecipient`側に持たせ、両者を突き合わせて
           `edited`(講師が配信前に内容を変えたか)を導出する(`data/assignment_proposal_data.py`)。
           生成時点の内容を上書きしてしまうと、あとから「AIが何を提案したか」を
           復元できなくなるため。
    """

    __tablename__ = "assignment_proposals"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    message_for_member = Column(String, nullable=True)
    aim = Column(String, nullable=False)
    rationale = Column(String, nullable=False)
    estimate_minutes = Column(Integer, nullable=False)
    materials = Column(JSON, nullable=False)
    progress = Column(JSON, nullable=False)
    theme_key = Column(String, nullable=False)
    generator = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=True)
    reject_reason = Column(String, nullable=True)
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(String, nullable=True)


class Certification(Base):
    """資格情報。

    !NOTE: `home_profile.certification_id`にUNIQUE制約があるため、1行は必ず1人の
           ユーザーの資格達成率にひも付く(複数ユーザー間で同じ資格の行を使い回さない)。
           ユーザーごとに独立した達成率を持たせるための設計であり、資格マスタでは無い。
    """

    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    achievement_percent = Column(Integer, nullable=False)


class HomeProfile(Base):
    """ホーム画面のプロフィール情報。

    !NOTE: 1ユーザーにつき1行(`user_id`はUNIQUE・NOT NULL)。氏名は`users.display_name`
           を参照するため列を持たない。ヒーローメッセージも表示のたびに`display_name`
           からテンプレートで組み立てる(`data/home_data.py`)ため列を持たない。
           強み(strengths)はUIデザイン上常に3件固定表示のため、リレーション化せず
           3スロット分のカラムとして持たせている。
    """

    __tablename__ = "home_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user_streak_days = Column(Integer, nullable=False)
    strength1_label = Column(String, nullable=False)
    strength1_tone = Column(String, nullable=False)
    strength2_label = Column(String, nullable=False)
    strength2_tone = Column(String, nullable=False)
    strength3_label = Column(String, nullable=False)
    strength3_tone = Column(String, nullable=False)
    certification_id = Column(
        Integer, ForeignKey("certifications.id"), nullable=False, unique=True
    )


class Department(Base):
    __tablename__ = "departments"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    icon = Column(String, nullable=False)
    color = Column(String, nullable=False)
    knowledge_count = Column(Integer, nullable=False)


class DepartmentMessage(Base):
    """課ごとの初期チャット履歴。

    !NOTE: `ordinal`は課内での表示順(1始まり)。フロントに返す`ChatMessage.id`は
           `f"{department_id}-m{ordinal}"`の形で組み立てて既存フォーマットと互換にしている。
    """

    __tablename__ = "department_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    role = Column(String, nullable=False)
    text = Column(String, nullable=False)
    ordinal = Column(Integer, nullable=False)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)


class QuizQuestion(Base):
    """クイズ出題データ。

    !NOTE: `source`は出典(試験回・問番号)を示す任意項目。サンプル問題(q_101等)には
           出典が無いため`nullable=True`にしている。
    """

    __tablename__ = "quiz_questions"

    id = Column(String, primary_key=True)
    category = Column(String, nullable=False)
    text = Column(String, nullable=False)
    choices = Column(JSON, nullable=False)
    correct_index = Column(Integer, nullable=False)
    explanation = Column(String, nullable=False)
    time_limit_sec = Column(Integer, nullable=False, default=90)
    source = Column(String, nullable=True)


class PocRun(Base):
    """強み解析PoCの1run分(3周のtrajectory・日報・レビュー・解析結果)。

    !NOTE: 仕様書(`example/Caliboo_強み解析_PoC_機能追加_基本仕様書.md`)§5が
           「3周と小規模なため、ループ状態を1つの型付きオブジェクトとして保持」と
           述べている通り、trajectory/diary/reviews/strengthsをリレーション分割せず
           JSON列に持たせる(既存の`Report.mood`/`QuizQuestion.choices`と同じJSON列運用)。

    !NOTE: `status`列は持たない。本PoCの生成は事前執筆コンテンツ+決定論的解析のため
           runは常に完了した状態でのみ保存される。`AssignmentSubmission`が導出可能な
           状態を列に持たない方針(`_resolve_status()`)と同様、常に固定値になる列を
           持たせると更新漏れの余地だけが増えるため。
    """

    __tablename__ = "poc_runs"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    persona_key = Column(String, nullable=False)
    subject_id = Column(String, nullable=False)
    label = Column(String, nullable=False)
    injected_persona = Column(String, nullable=True)
    trajectory = Column(JSON, nullable=False)
    diary = Column(JSON, nullable=False)
    reviews = Column(JSON, nullable=False)
    strengths = Column(JSON, nullable=False)
    trace = Column(JSON, nullable=False)
    created_at = Column(String, nullable=False)


class ProgressCategory(Base):
    __tablename__ = "progress_categories"

    id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    percent = Column(Integer, nullable=False)


class RelatedQuestion(Base):
    __tablename__ = "related_questions"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    question_count = Column(Integer, nullable=False)
    tags = Column(JSON, nullable=False)


class Report(Base):
    """日報(KPT)の保存レコード。

    !NOTE: `try`はPythonの予約語のため、属性名は`try_`にしつつ物理カラム名のみ`try`にしている
           (`schemas/report.py`の`ReportRequest.try_`と同じ回避方法)。
    """

    __tablename__ = "reports"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)
    keep = Column(String, nullable=False)
    problem = Column(String, nullable=False)
    try_ = Column("try", String, nullable=False)
    mood = Column(JSON, nullable=True)
    mood_comment = Column(String, nullable=False, default="")
    status = Column(String, nullable=False)
    saved_at = Column(String, nullable=False)
