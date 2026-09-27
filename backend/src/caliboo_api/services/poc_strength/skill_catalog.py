"""強み解析の判定材料(スキル辞書・確信度表・育成アクション表)。

!NOTE: このモジュールはペルソナ台本(`data/poc_persona_scripts.py`)より先に確定させ、
       以後変更しない前提で扱う。台本を書いてからキーワードを足すと、台本に合わせて
       辞書を調整したトートロジーになり、検証(a)(仕様書§8)が「解析が壊れていないこと」
       を示す独立した検査として機能しなくなるため。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillDefinition:
    """SFIAスキル1件と、それを本文から検出するためのキーワード。

    `themes`はCliftonStrengths(層2)のテーマ候補。
    """

    code: str
    name: str
    keywords: tuple[str, ...]
    themes: tuple[str, ...]


SKILL_CATALOG: tuple[SkillDefinition, ...] = (
    SkillDefinition(
        code="DBAD",
        name="データベース設計/管理",
        keywords=("SQL", "クエリ", "テーブル", "集計", "インデックス", "結合"),
        themes=("Analytical", "Deliberative"),
    ),
    SkillDefinition(
        code="DTAN",
        name="データ分析/可視化",
        keywords=("可視化", "ダッシュボード", "グラフ", "推移", "内訳"),
        themes=("Analytical", "Input"),
    ),
    SkillDefinition(
        code="PROG",
        name="プログラミング/ソフトウェア開発",
        keywords=("スクリプト", "実装", "コード", "関数", "自動化"),
        themes=("Achiever", "Learner"),
    ),
    SkillDefinition(
        code="DOCM",
        name="文書作成/ナレッジ管理",
        keywords=("ドキュメント", "手順書", "マニュアル", "書き起こ", "文章"),
        themes=("Communication", "Discipline"),
    ),
    SkillDefinition(
        code="TEST",
        name="テスト/品質確認",
        keywords=("テスト", "不具合", "バグ", "検算", "エッジケース"),
        themes=("Deliberative", "Restorative"),
    ),
    SkillDefinition(
        code="RLMT",
        name="関係構築/コミュニケーション",
        keywords=("ヒアリング", "すり合わせ", "調整", "橋渡し", "傾聴"),
        themes=("Communication", "Woo"),
    ),
)

# 確信度と判定ステータスの対応。
#
# !NOTE: 確信度はキーワードの「出現回数」ではなく「独立した裏付けの種類数」
#        (軌跡 / 日報 / レビューのうち何種類から裏付けられたか)だけで決める。
#        出現回数を主軸にすると、単に記述量が多いペルソナほど確信度が高くなり、
#        「根拠の強さ」ではなく「文章の長さ」を測ることになるため。
#        仕様書§10で未決だった「評価保留のconfidenceしきい値」は、この表で確定させる。
SUPPORT_KINDS = ("trajectory", "diary", "review")

CONFIDENCE_BY_SUPPORT_COUNT: dict[int, float] = {3: 0.85, 2: 0.6, 1: 0.35}

# 確信度がこの値未満の強みは「評価保留」として扱い、断定しない(仕様書§9の過剰付与抑制)。
TENTATIVE_THRESHOLD = 0.5
CONFIRMED_THRESHOLD = 0.75

# SFIAレベルは新人を対象とする前提のため1〜2のみを出す。
LEVEL_WHEN_FULLY_SUPPORTED = 2
LEVEL_WHEN_PARTIALLY_SUPPORTED = 1

# Will-Skill象限ごとの育成方針(仕様書§7の「育成アクションはskill_codeとquadrantの組で出し分ける」)。
QUADRANT_POLICY: dict[str, str] = {
    "High Will / Low Skill": "意欲が先行している段階のため、基礎課題の反復で土台を底上げする",
    "High Will / High Skill": "意欲・技能とも揃っているため、応用範囲を広げる課題で伸ばす",
    "Low Will / High Skill": "技能は足りているため、裁量のある課題を任せて動機づけを取り戻す",
    "Low Will / Low Skill": "まず成功体験を作るため、短時間で完了できる課題から始める",
}

# skill_codeを安定キーとした教育コンテンツ対応(仕様書§7)。
GROWTH_CONTENT_BY_SKILL: dict[str, dict[str, str]] = {
    "DBAD": {"title": "SQL・データ処理の課題", "contentTag": "sql-drill"},
    "DTAN": {"title": "データ可視化の課題", "contentTag": "dataviz-drill"},
    "PROG": {"title": "実装・自動化の課題", "contentTag": "coding-drill"},
    "DOCM": {"title": "手順書作成の課題", "contentTag": "docs-drill"},
    "TEST": {"title": "テスト設計の課題", "contentTag": "testing-drill"},
    "RLMT": {"title": "ヒアリング・調整の課題", "contentTag": "communication-drill"},
}


def find_skill(code: str) -> SkillDefinition | None:
    """スキルコードから定義を引く。未知のコードはNoneを返す。"""
    for skill in SKILL_CATALOG:
        if skill.code == code:
            return skill
    return None
