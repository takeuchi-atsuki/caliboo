"""AIの課題案(BACKLOG #17)データのDBアクセス層。"""

from datetime import datetime, timezone
from enum import Enum, auto
from zoneinfo import ZoneInfo

from sqlalchemy import literal, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from caliboo_api.data.assignment_data import fetch_visible_assignment_statuses, insert_assignment
from caliboo_api.data.account_data import is_active
from caliboo_api.db import session_scope
from caliboo_api.models import (
    Assignment,
    AssignmentProposal,
    AssignmentRecipient,
    AssignmentSubmission,
    Report,
    User,
)
from caliboo_api.schemas.assignment_proposal import (
    ProposalDetail,
    ProposalListItem,
    ProposalMember,
    ProposalStatus,
    ProposalUserRef,
)
from caliboo_api.services.assignment_proposal import pipeline
from caliboo_api.services.assignment_proposal.pipeline import RECENT_REPORT_COUNT

# !NOTE: FBの材料日付(`ProposalMaterial.date`)は、対象者・講師が実際に読む画面表示に
#        合わせて日本時間(Asia/Tokyo)の日付にする。`feedback_at`はUTCのISO文字列で
#        保存しているため(`data/assignment_data.py`)、そのまま先頭10桁を切り出すと
#        UTCの日付になり、日本時間では日付が変わっている時間帯にズレが生じるため。
_JST = ZoneInfo("Asia/Tokyo")


class ProposalCreateError(Enum):
    TARGET_NOT_FOUND = auto()


class ProposalActionError(Enum):
    NOT_FOUND = auto()
    NOT_PENDING = auto()


def _normalize_message(text: str | None) -> str | None:
    """前後の空白を除去し、空文字になれば`None`にする(`messageForMember`の正規化)。"""
    stripped = (text or "").strip()
    return stripped or None


def _to_jst_date(iso_timestamp: str | None) -> str | None:
    """UTCのISO日時文字列を日本時間の日付(`YYYY-MM-DD`)へ変換する。値が無ければ`None`。"""
    if not iso_timestamp:
        return None
    return datetime.fromisoformat(iso_timestamp).astimezone(_JST).date().isoformat()


def _resolve_proposal_status(proposal: AssignmentProposal) -> ProposalStatus:
    if proposal.assignment_id is not None:
        return "approved"
    if proposal.decided_at is not None:
        return "rejected"
    return "pending"


def _to_list_item(proposal: AssignmentProposal, target_user: User) -> ProposalListItem:
    return ProposalListItem(
        id=proposal.id,
        target=ProposalUserRef(id=target_user.id, displayName=target_user.display_name),
        title=proposal.title,
        aim=proposal.aim,
        status=_resolve_proposal_status(proposal),
        createdAt=proposal.created_at,
        decidedAt=proposal.decided_at,
    )


def _resolve_edited(proposal: AssignmentProposal, session: Session) -> bool:
    """配信済み(`assignment_id`あり)の課題案について、配信内容が生成時点の内容と
    異なるかを比較して導出する。それ以外(確認待ち・見送り)は常に`False`。
    """
    if proposal.assignment_id is None:
        return False
    assignment = session.get(Assignment, proposal.assignment_id)
    if assignment is None:
        return False
    recipient = (
        session.query(AssignmentRecipient)
        .filter(AssignmentRecipient.assignment_id == proposal.assignment_id)
        .first()
    )
    delivered_message = (
        _normalize_message(recipient.message_for_member) if recipient is not None else None
    )
    return (
        assignment.title != proposal.title
        or assignment.body != proposal.body
        or delivered_message != _normalize_message(proposal.message_for_member)
    )


def _to_detail(proposal: AssignmentProposal, session: Session) -> ProposalDetail:
    target_user = session.get(User, proposal.target_user_id)
    list_item = _to_list_item(proposal, target_user)

    decided_by = None
    if proposal.decided_by is not None:
        decider = session.get(User, proposal.decided_by)
        if decider is not None:
            decided_by = ProposalUserRef(id=decider.id, displayName=decider.display_name)

    return ProposalDetail(
        **list_item.model_dump(),
        body=proposal.body,
        messageForMember=proposal.message_for_member,
        rationale=proposal.rationale,
        estimateMinutes=proposal.estimate_minutes,
        materials=proposal.materials,
        progress=proposal.progress,
        generator=proposal.generator,
        assignmentId=proposal.assignment_id,
        rejectReason=proposal.reject_reason,
        decidedBy=decided_by,
        edited=_resolve_edited(proposal, session),
    )


def _find_pending_proposal(session: Session, target_user_id: int) -> AssignmentProposal | None:
    return (
        session.query(AssignmentProposal)
        .filter(
            AssignmentProposal.target_user_id == target_user_id,
            AssignmentProposal.assignment_id.is_(None),
            AssignmentProposal.decided_at.is_(None),
        )
        .order_by(AssignmentProposal.created_at.desc(), AssignmentProposal.id.desc())
        .first()
    )


def _recent_reports(session: Session, user_id: int) -> list[dict]:
    """対象者の直近の提出済み日報を、新しい順に最大`RECENT_REPORT_COUNT`件返す。

    下書き(status=="draft")・他人の日報は対象にしない。
    """
    rows = (
        session.query(Report)
        .filter(Report.status == "submitted", Report.user_id == user_id)
        .order_by(Report.date.desc(), Report.id.desc())
        .limit(RECENT_REPORT_COUNT)
        .all()
    )
    return [
        {
            "date": row.date,
            "problem": row.problem,
            "try": row.try_,
            "keep": row.keep,
            "mood": row.mood or [],
            "moodComment": row.mood_comment,
        }
        for row in rows
    ]


def _all_feedbacks(session: Session, user_id: int) -> list[dict]:
    """対象者の提出への講師フィードバックを、確定日時の古い順に全件返す(他人の提出・
    未確定(feedback_comment無し)のフィードバックは対象にしない)。
    """
    rows = (
        session.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.user_id == user_id,
            AssignmentSubmission.feedback_comment.isnot(None),
        )
        .order_by(AssignmentSubmission.feedback_at, AssignmentSubmission.id)
        .all()
    )
    return [
        {"date": _to_jst_date(row.feedback_at), "comment": row.feedback_comment} for row in rows
    ]


def _excluded_themes(session: Session, user_id: int) -> set[str]:
    """配信済み・見送り済みのテーマキー(フォールバックは`providers.py`側で除外しない)。"""
    rows = (
        session.query(AssignmentProposal)
        .filter(AssignmentProposal.target_user_id == user_id)
        .filter(
            (AssignmentProposal.assignment_id.isnot(None))
            | (AssignmentProposal.decided_at.isnot(None))
        )
        .all()
    )
    return {row.theme_key for row in rows}


def _run_generator(session: Session, target_user: User) -> dict:
    return pipeline.generate_proposal(
        member_name=target_user.display_name,
        reports=_recent_reports(session, target_user.id),
        submission_statuses=fetch_visible_assignment_statuses(session, target_user.id),
        feedbacks=_all_feedbacks(session, target_user.id),
        excluded_themes=_excluded_themes(session, target_user.id),
    )


def list_proposals(
    status: ProposalStatus | None, assignment_id: int | None
) -> tuple[list[ProposalListItem], list[ProposalMember], int]:
    """課題案一覧・生成対象の新入社員一覧・確認待ち件数を返す。

    `assignment_id`を指定した場合は`status`を無視し、その課題を配信した課題案のみ
    (通常は0〜1件)を返す。
    """
    with session_scope() as session:
        proposals = (
            session.query(AssignmentProposal)
            .order_by(AssignmentProposal.created_at.desc(), AssignmentProposal.id.desc())
            .all()
        )
        if assignment_id is not None:
            proposals = [p for p in proposals if p.assignment_id == assignment_id]
        else:
            effective_status = status or "pending"
            proposals = [p for p in proposals if _resolve_proposal_status(p) == effective_status]

        users_by_id = {user.id: user for user in session.query(User).all()}
        list_items = [
            _to_list_item(proposal, users_by_id[proposal.target_user_id])
            for proposal in proposals
            if proposal.target_user_id in users_by_id
        ]

        # `pendingCount`は確認待ちの課題案の件数そのもの(タブの件数バッジに使う)。
        # 「確認待ちを持つ新入社員の人数」と一致する前提(新入社員1人につき確認待ちは
        # 高々1件になるよう`create_or_get_pending_proposal`が保証する)だが、
        # 名前の意味どおり「件数」を直接数える。
        pending_proposals = [
            proposal
            for proposal in session.query(AssignmentProposal).all()
            if _resolve_proposal_status(proposal) == "pending"
        ]
        pending_target_ids = {proposal.target_user_id for proposal in pending_proposals}
        members = (
            session.query(User)
            .filter(User.role == "member")
            .order_by(User.display_name.asc(), User.id.asc())
            .all()
        )
        member_items = [
            ProposalMember(
                id=member.id,
                displayName=member.display_name,
                hasPending=member.id in pending_target_ids,
            )
            for member in members
        ]

        return list_items, member_items, len(pending_proposals)


def create_or_get_pending_proposal(
    user_id: int,
) -> tuple[ProposalDetail, bool] | ProposalCreateError:
    """対象の新入社員に確認待ちの課題案が既にあればそれを返し(冪等)、無ければ生成する。

    戻り値の`bool`は新規作成なら`True`(呼び出し側が201を返すために使う)。
    """
    with session_scope() as session:
        target_user = session.get(User, user_id)
        if target_user is None or target_user.role != "member" or not is_active(session, user_id):
            return ProposalCreateError.TARGET_NOT_FOUND

        existing = _find_pending_proposal(session, user_id)
        if existing is not None:
            return _to_detail(existing, session), False

        result = _run_generator(session, target_user)
        proposal, is_new = save_generated_proposal(
            session, user_id, result, pipeline.generator_name())
        session.commit()
        return _to_detail(proposal, session), is_new


def proposal_inputs(session: Session, user_id: int) -> dict:
    return dict(reports=_recent_reports(session, user_id),
                submission_statuses=fetch_visible_assignment_statuses(session, user_id),
                feedbacks=_all_feedbacks(session, user_id)[-20:],
                excluded_themes=sorted(_excluded_themes(session, user_id)))


def save_generated_proposal(session: Session, user_id: int, result: dict,
                            generator: str) -> tuple[AssignmentProposal, bool]:
    """検証済みの出力を保存する。ジョブ完了と同じトランザクションで利用できる。"""
    values = dict(
        target_user_id=user_id, title=result["title"], body=result["body"],
        message_for_member=_normalize_message(result["messageForMember"]),
        aim=result["aim"], rationale=result["rationale"],
        estimate_minutes=result["estimateMinutes"], materials=result["materials"],
        progress=result["progress"], theme_key=result["themeKey"],
        generator=generator, created_at=datetime.now(timezone.utc).isoformat(),
    )
    pending = select(AssignmentProposal.id).where(
        AssignmentProposal.target_user_id == user_id,
        AssignmentProposal.assignment_id.is_(None), AssignmentProposal.decided_at.is_(None),
    ).exists()
    # !NOTE: 推論中に別リクエストが生成した確認待ちを増やさない。判定とINSERTを一文にする。
    source = select(*[literal(value, type_=AssignmentProposal.__table__.c[key].type)
                      for key, value in values.items()]).where(~pending)
    inserted = session.execute(insert(AssignmentProposal).from_select(list(values), source))
    proposal = _find_pending_proposal(session, user_id)
    return proposal, bool(inserted.rowcount)


def get_proposal_detail(proposal_id: int) -> ProposalDetail | None:
    with session_scope() as session:
        proposal = session.get(AssignmentProposal, proposal_id)
        if proposal is None:
            return None
        return _to_detail(proposal, session)


def _update_if_still_pending(session: Session, proposal_id: int, values: dict) -> int:
    """`id`が一致し、かつ確認待ち(`assignment_id`・`decided_at`とも未設定)の行だけを
    条件付きUPDATEする。マッチした行数を返す(0件なら「確認待ちではなかった」)。

    !NOTE: 事前に`_resolve_proposal_status()`で確認してからUPDATEする2段階の実装だと、
           確認とUPDATEの間に別リクエストが先に配信・見送りを確定させた場合、後勝ちで
           上書きしてしまう(例: 見送り済みの課題案に課題が作られてしまう)。`WHERE`句に
           確認待ちの条件そのものを含めることで、更新自体を原子的にする(I1)。
    """
    return (
        session.query(AssignmentProposal)
        .filter(
            AssignmentProposal.id == proposal_id,
            AssignmentProposal.assignment_id.is_(None),
            AssignmentProposal.decided_at.is_(None),
        )
        .update(values, synchronize_session=False)
    )


def approve_proposal(
    proposal_id: int,
    title: str,
    body: str,
    message_for_member: str,
    admin_user_id: int,
) -> ProposalDetail | ProposalActionError:
    """課題案を配信する(課題作成・配信先登録・課題案の決定を1トランザクションで行う)。"""
    with session_scope() as session:
        proposal = session.get(AssignmentProposal, proposal_id)
        if proposal is None:
            return ProposalActionError.NOT_FOUND

        assignment = insert_assignment(session, title, body)
        session.add(
            AssignmentRecipient(
                assignment_id=assignment.id,
                user_id=proposal.target_user_id,
                message_for_member=_normalize_message(message_for_member),
            )
        )
        updated_rows = _update_if_still_pending(
            session,
            proposal_id,
            {
                "assignment_id": assignment.id,
                "decided_by": admin_user_id,
                "decided_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if updated_rows == 0:
            session.rollback()
            return ProposalActionError.NOT_PENDING

        session.commit()
        session.refresh(proposal)
        return _to_detail(proposal, session)


def reject_proposal(
    proposal_id: int, reason: str | None, admin_user_id: int
) -> ProposalDetail | ProposalActionError:
    with session_scope() as session:
        proposal = session.get(AssignmentProposal, proposal_id)
        if proposal is None:
            return ProposalActionError.NOT_FOUND

        updated_rows = _update_if_still_pending(
            session,
            proposal_id,
            {
                "reject_reason": reason,
                "decided_by": admin_user_id,
                "decided_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        if updated_rows == 0:
            session.rollback()
            return ProposalActionError.NOT_PENDING

        session.commit()
        session.refresh(proposal)
        return _to_detail(proposal, session)
