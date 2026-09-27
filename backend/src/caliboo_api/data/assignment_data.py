"""課題演習データのDBアクセス層。"""

from datetime import datetime, timezone
from enum import Enum, auto

from sqlalchemy.orm import Session

from caliboo_api.db import session_scope
from caliboo_api.models import Assignment, AssignmentRecipient, AssignmentSubmission, User
from caliboo_api.schemas.assignment import (
    AssignmentDetail,
    AssignmentListItem,
    AssignmentStatus,
    AssignmentSubmissionDetail,
    AssignmentTarget,
    MemberSubmission,
    MemberUser,
)


class SubmissionSaveError(Enum):
    ASSIGNMENT_NOT_FOUND = auto()
    ALREADY_REVIEWED = auto()


class FeedbackSaveError(Enum):
    ASSIGNMENT_NOT_FOUND = auto()
    USER_NOT_FOUND = auto()
    NOT_SUBMITTED = auto()


def _resolve_status(submission: AssignmentSubmission | None) -> AssignmentStatus:
    if submission is None:
        return "not_submitted"
    if submission.feedback_comment is not None:
        return "reviewed"
    return "submitted"


def _to_submission_detail(
    submission: AssignmentSubmission | None,
) -> AssignmentSubmissionDetail | None:
    if submission is None:
        return None
    return AssignmentSubmissionDetail(
        answerText=submission.answer_text,
        submittedAt=submission.submitted_at,
        feedbackComment=submission.feedback_comment,
        feedbackAt=submission.feedback_at,
    )


def _to_detail(
    assignment: Assignment,
    submission: AssignmentSubmission | None,
    target: AssignmentTarget | None = None,
    message_for_member: str | None = None,
) -> AssignmentDetail:
    return AssignmentDetail(
        id=assignment.id,
        title=assignment.title,
        body=assignment.body,
        status=_resolve_status(submission),
        createdAt=assignment.created_at,
        submission=_to_submission_detail(submission),
        target=target,
        messageForMember=message_for_member or None,
    )


def _to_member_submission(
    user: User, submission: AssignmentSubmission | None
) -> MemberSubmission:
    return MemberSubmission(
        user=MemberUser(id=user.id, displayName=user.display_name),
        status=_resolve_status(submission),
        submission=_to_submission_detail(submission),
    )


def _get_submission(
    session: Session, assignment_id: int, user_id: int
) -> AssignmentSubmission | None:
    return (
        session.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.user_id == user_id,
        )
        .first()
    )


def _get_recipient(session: Session, assignment_id: int) -> AssignmentRecipient | None:
    return (
        session.query(AssignmentRecipient)
        .filter(AssignmentRecipient.assignment_id == assignment_id)
        .first()
    )


def _recipients_by_assignment(
    session: Session, assignment_ids: list[int]
) -> dict[int, AssignmentRecipient]:
    """`assignment_id → AssignmentRecipient`の生の対応表を返す(表示用ではなく、
    「個人宛てかどうか」の可視性判定に使う。`_target_map()`と違い、対象ユーザーの
    解決可否に関わらず配信先行の有無をそのまま表す)。
    """
    if not assignment_ids:
        return {}
    return {
        recipient.assignment_id: recipient
        for recipient in session.query(AssignmentRecipient)
        .filter(AssignmentRecipient.assignment_id.in_(assignment_ids))
        .all()
    }


def _target_map(
    session: Session, recipients_by_assignment: dict[int, AssignmentRecipient]
) -> dict[int, AssignmentTarget]:
    """表示用に、配信先を`assignment_id → AssignmentTarget`へ変換する。

    !NOTE: 可視性の判定(「個人宛てかどうか」)にはこの戻り値ではなく
           `_recipients_by_assignment()`の結果を使うこと。対象ユーザーが解決できない
           行はここでは除外されるため、これを可視性判定に使うと「配信先行はあるのに
           解決できないユーザー」を誤って全員宛てとして扱ってしまう(I6)。
    """
    if not recipients_by_assignment:
        return {}
    user_ids = {recipient.user_id for recipient in recipients_by_assignment.values()}
    users_by_id = {
        user.id: user for user in session.query(User).filter(User.id.in_(user_ids)).all()
    }
    return {
        assignment_id: AssignmentTarget(
            id=recipient.user_id, displayName=users_by_id[recipient.user_id].display_name
        )
        for assignment_id, recipient in recipients_by_assignment.items()
        if recipient.user_id in users_by_id
    }


def _to_target_single(
    recipient: AssignmentRecipient | None, session: Session
) -> AssignmentTarget | None:
    if recipient is None:
        return None
    user = session.get(User, recipient.user_id)
    if user is None:
        return None
    return AssignmentTarget(id=user.id, displayName=user.display_name)


def fetch_assignment_list(user_id: int, role: str) -> list[AssignmentListItem]:
    """課題一覧を作成日時降順(同値はid降順)で返す。

    `status`は常に呼び出したユーザー本人の提出状況を表す(講師には提出が無いため、
    常に`not_submitted`になる)。新入社員(`role == "member"`)には、全員宛ての課題と
    自分宛ての課題だけを返す(他人宛ての課題は一覧にも出さない)。
    """
    with session_scope() as session:
        assignments = (
            session.query(Assignment)
            .order_by(Assignment.created_at.desc(), Assignment.id.desc())
            .all()
        )
        recipients = _recipients_by_assignment(session, [a.id for a in assignments])
        targets = _target_map(session, recipients)
        if role == "member":
            assignments = [
                assignment
                for assignment in assignments
                if assignment.id not in recipients or recipients[assignment.id].user_id == user_id
            ]

        submissions_by_assignment = {
            submission.assignment_id: submission
            for submission in session.query(AssignmentSubmission)
            .filter(AssignmentSubmission.user_id == user_id)
            .all()
        }
        return [
            AssignmentListItem(
                id=assignment.id,
                title=assignment.title,
                status=_resolve_status(submissions_by_assignment.get(assignment.id)),
                createdAt=assignment.created_at,
                target=targets.get(assignment.id),
            )
            for assignment in assignments
        ]


def get_assignment_detail(assignment_id: int, user_id: int, role: str) -> AssignmentDetail | None:
    """新入社員(`role == "member"`)が他人宛ての課題を指定した場合は`None`(404)にする。"""
    with session_scope() as session:
        assignment = session.get(Assignment, assignment_id)
        if assignment is None:
            return None
        recipient = _get_recipient(session, assignment_id)
        if role == "member" and recipient is not None and recipient.user_id != user_id:
            return None
        submission = _get_submission(session, assignment_id, user_id)
        return _to_detail(
            assignment,
            submission,
            _to_target_single(recipient, session),
            recipient.message_for_member if recipient else None,
        )


def insert_assignment(session: Session, title: str, body: str) -> Assignment:
    """課題行をINSERTする(コミットしない)。

    !NOTE: コミットは呼び出し元が行う。手動作成(`create_assignment`)は単独でコミット
           するが、課題案の配信(`data/assignment_proposal_data.py`)は課題行の作成・
           配信先(`AssignmentRecipient`)の作成・課題案の状態更新を1トランザクションに
           まとめる必要があるため、コミットしないこの関数を両方から共通で呼ぶ。
    """
    assignment = Assignment(
        title=title,
        body=body,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    session.add(assignment)
    session.flush()
    return assignment


def create_assignment(session: Session, title: str, body: str) -> AssignmentDetail:
    assignment = insert_assignment(session, title, body)
    session.commit()
    session.refresh(assignment)
    return _to_detail(assignment, None)


def save_submission(
    session: Session, assignment_id: int, user_id: int, answer_text: str
) -> AssignmentDetail | SubmissionSaveError:
    """回答を提出(または上書き再提出)する。

    !NOTE: フィードバック確定後(reviewed)の再提出は拒否する。フィードバック文が
           特定の回答文を前提に書かれているため、回答だけ差し替わるとコメントが
           的外れな状態で残ってしまう。フィードバック前の再提出は同じ提出行を
           UPDATEする(新しい行を追加しない)。

    !NOTE: 個人宛て課題で対象者以外が提出しようとした場合も`ASSIGNMENT_NOT_FOUND`を
           返す(存在しない課題と区別しない。他人宛て課題の存在自体を教えないため)。
    """
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        return SubmissionSaveError.ASSIGNMENT_NOT_FOUND

    recipient = _get_recipient(session, assignment_id)
    if recipient is not None and recipient.user_id != user_id:
        return SubmissionSaveError.ASSIGNMENT_NOT_FOUND

    submission = _get_submission(session, assignment_id, user_id)
    if submission is not None and submission.feedback_comment is not None:
        return SubmissionSaveError.ALREADY_REVIEWED

    submitted_at = datetime.now(timezone.utc).isoformat()
    if submission is None:
        submission = AssignmentSubmission(
            assignment_id=assignment_id,
            user_id=user_id,
            answer_text=answer_text,
            submitted_at=submitted_at,
        )
        session.add(submission)
    else:
        submission.answer_text = answer_text
        submission.submitted_at = submitted_at

    session.commit()
    session.refresh(assignment)
    session.refresh(submission)
    return _to_detail(
        assignment,
        submission,
        _to_target_single(recipient, session),
        recipient.message_for_member if recipient else None,
    )


def fetch_member_submissions(
    session: Session, assignment_id: int
) -> list[MemberSubmission] | None:
    """講師向け: 課題1件についての提出状況を氏名昇順で返す。

    個人宛て課題(配信先が1人に絞られている課題)は、その対象者1人分だけを返す。
    全員宛て課題は、role=memberの全ユーザー(未提出者を含む)を返す。
    課題が存在しない場合は`None`を返す。
    """
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        return None

    recipient = _get_recipient(session, assignment_id)
    if recipient is not None:
        target_user = session.get(User, recipient.user_id)
        members = [target_user] if target_user is not None else []
    else:
        members = (
            session.query(User)
            .filter(User.role == "member")
            .order_by(User.display_name.asc(), User.id.asc())
            .all()
        )

    submissions_by_user = {
        submission.user_id: submission
        for submission in session.query(AssignmentSubmission)
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .all()
    }
    return [
        _to_member_submission(member, submissions_by_user.get(member.id)) for member in members
    ]


def save_member_feedback(
    session: Session, assignment_id: int, target_user_id: int, comment: str
) -> MemberSubmission | FeedbackSaveError:
    """講師が特定の新入社員の提出にフィードバックコメントを保存する(上書き可)。

    個人宛て課題で対象外の新入社員が指定された場合も`USER_NOT_FOUND`を返す
    (課題自体が対象外新入社員には存在しないものとして扱う。404)。
    """
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        return FeedbackSaveError.ASSIGNMENT_NOT_FOUND

    target_user = session.get(User, target_user_id)
    if target_user is None or target_user.role != "member":
        return FeedbackSaveError.USER_NOT_FOUND

    recipient = _get_recipient(session, assignment_id)
    if recipient is not None and recipient.user_id != target_user_id:
        return FeedbackSaveError.USER_NOT_FOUND

    submission = _get_submission(session, assignment_id, target_user_id)
    if submission is None:
        return FeedbackSaveError.NOT_SUBMITTED

    submission.feedback_comment = comment
    submission.feedback_at = datetime.now(timezone.utc).isoformat()
    session.commit()
    session.refresh(submission)
    session.refresh(target_user)
    return _to_member_submission(target_user, submission)


def fetch_visible_assignment_statuses(session: Session, user_id: int) -> list[AssignmentStatus]:
    """新入社員から見える課題(全員宛て+本人宛て)それぞれの提出状況を返す。

    課題案生成時の`progress`(提出数・レビュー済み数・未提出数)の算出に使う
    (`data/assignment_proposal_data.py`)。
    """
    assignments = session.query(Assignment).all()
    recipients = _recipients_by_assignment(session, [a.id for a in assignments])
    visible_ids = [
        assignment.id
        for assignment in assignments
        if assignment.id not in recipients or recipients[assignment.id].user_id == user_id
    ]
    if not visible_ids:
        return []
    submissions_by_assignment = {
        submission.assignment_id: submission
        for submission in session.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.user_id == user_id,
            AssignmentSubmission.assignment_id.in_(visible_ids),
        )
        .all()
    }
    return [_resolve_status(submissions_by_assignment.get(aid)) for aid in visible_ids]
