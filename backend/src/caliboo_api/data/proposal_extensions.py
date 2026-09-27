"""日報提出イベントと課題案エージェントの接続。"""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from caliboo_api.data.account_data import is_active
from caliboo_api.data.assignment_data import fetch_visible_assignment_statuses
from caliboo_api.data.assignment_proposal_data import create_or_get_pending_proposal
from caliboo_api.extension_models import ProposalAutomation


def auto_propose(session: Session, user_id: int) -> None:
    if not is_active(session, user_id):
        return
    statuses = fetch_visible_assignment_statuses(session, user_id)
    if statuses.count("not_submitted") < 3:
        return
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    session.execute(insert(ProposalAutomation).values(user_id=user_id, last_date="").
                    on_conflict_do_nothing())
    updated = session.query(ProposalAutomation).filter(
        ProposalAutomation.user_id == user_id, ProposalAutomation.last_date != today,
    ).update({"last_date": today})
    session.commit()
    if updated:
        create_or_get_pending_proposal(user_id)
