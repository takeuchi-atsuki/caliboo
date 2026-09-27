"""日報(KPT)データのDBアクセス層。"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from caliboo_api.db import session_scope
from caliboo_api.models import Report
from caliboo_api.schemas.report import ReportDraftItem, ReportHistoryItem, ReportRequest


def create_report(session: Session, user_id: int, payload: ReportRequest) -> Report:
    """日報を1件INSERTし、採番されたPKを含むレコードを返す。"""
    report = Report(
        user_id=user_id,
        date=payload.date,
        keep=payload.keep,
        problem=payload.problem,
        try_=payload.try_,
        mood=payload.mood,
        mood_comment=payload.moodComment,
        status=payload.status,
        saved_at=datetime.now(timezone.utc).isoformat(),
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def fetch_report_history(user_id: int) -> list[ReportHistoryItem]:
    """本人が提出済み(status=="submitted")の日報履歴を、日付降順(同日付はID降順)で返す。

    `id`はsqlite_autoincrementのため単調増加し、提出順の代理として使える。
    """
    with session_scope() as session:
        rows = (
            session.query(Report)
            .filter(Report.status == "submitted", Report.user_id == user_id)
            .order_by(Report.date.desc(), Report.id.desc())
            .all()
        )
        return [
            ReportHistoryItem(
                date=row.date,
                keep=row.keep,
                problem=row.problem,
                try_=row.try_,
                mood=row.mood or [],
                moodComment=row.mood_comment,
            )
            for row in rows
        ]


def fetch_draft_list(user_id: int) -> list[ReportDraftItem]:
    """本人の下書き(status=="draft")を、保存日時(saved_at)降順で返す。

    !NOTE: 提出済み履歴は`date`降順だが、下書き一覧は直近に作業していたものを
           見つけやすくするため`saved_at`降順にしている。
    """
    with session_scope() as session:
        rows = (
            session.query(Report)
            .filter(Report.status == "draft", Report.user_id == user_id)
            .order_by(Report.saved_at.desc(), Report.id.desc())
            .all()
        )
        return [
            ReportDraftItem(
                id=row.id,
                date=row.date,
                savedAt=row.saved_at,
                keep=row.keep,
                problem=row.problem,
                try_=row.try_,
                mood=row.mood or [],
                moodComment=row.mood_comment,
            )
            for row in rows
        ]


def delete_draft(session: Session, user_id: int, report_id: int) -> bool:
    """本人の下書きを1件削除する。削除できた場合`True`、対象が無ければ`False`を返す。

    !NOTE: 対象が下書きでない(提出済み)、または他人の日報である場合は、存在しない
           場合と同様に扱う(呼び出し元で404にする)。他人の下書きIDが存在すること
           自体を第三者に知らせないため、403ではなく404にする。
    """
    report = session.get(Report, report_id)
    if report is None or report.status != "draft" or report.user_id != user_id:
        return False
    session.delete(report)
    session.commit()
    return True
