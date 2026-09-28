"""ホーム画面データのDBアクセス層。

!NOTE: `HomeShortcut`(ショートカットカード)は固定リンク集でユーザー状態に依存しないため、
       DBテーブル化せずコード定数のまま保持している。
"""

from caliboo_api.db import session_scope
from caliboo_api.extension_models import StrengthCandidate
from caliboo_api.models import Certification, HomeProfile, User
from caliboo_api.schemas.home import (
    HomeCertification,
    HomeHero,
    HomeShortcut,
    HomeStrength,
    HomeSummary,
    HomeUser,
)

_SHORTCUTS = [
    # !NOTE: 日報はホームのふり返りパネルに専用導線があるため、ここは課題への入口にする。
    HomeShortcut(
        icon="ph-bold ph-clipboard-text",
        title="課題に取り組む",
        description="課題・フィードバックを確認",
        to="/assignments",
        tone="orange",
    ),
    HomeShortcut(
        icon="ph-bold ph-graduation-cap",
        title="資格勉強",
        description="過去問・質問",
        to="/study",
        tone="blue",
    ),
    HomeShortcut(
        icon="ph-bold ph-users-three",
        title="OJT",
        description="AIメンターに相談",
        to="/ojt",
        tone="green",
    ),
]


def fetch_home_summary(user_id: int) -> HomeSummary:
    """ログイン中のユーザー本人のホームサマリを返す。

    !NOTE: `hero.message`はDB列を持たず、`users.display_name`からテンプレート
           (`おかえり、{name}さん！今日の振り返りをしよう`)で組み立てる。
    """
    with session_scope() as session:
        user = session.get(User, user_id)
        profile = session.query(HomeProfile).filter(HomeProfile.user_id == user_id).first()
        certification = session.get(Certification, profile.certification_id)

        return HomeSummary(
            user=HomeUser(name=user.display_name, streakDays=profile.user_streak_days),
            hero=HomeHero(message=f"おかえり、{user.display_name}さん！今日の振り返りをしよう"),
            certification=HomeCertification(
                name=certification.name,
                achievementPercent=certification.achievement_percent,
            ),
            strengths=[
                HomeStrength(label=row.label, tone="green", evidence=row.evidence,
                             growthAction=row.growth_action)
                for row in session.query(StrengthCandidate).filter_by(
                    user_id=user_id, status="approved").order_by(StrengthCandidate.id.desc())
            ],
            shortcuts=_SHORTCUTS,
        )
