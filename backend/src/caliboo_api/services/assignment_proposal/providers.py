"""課題案生成のプラガブルな抽象化層(`services/poc_strength/providers.py`の構成を踏襲)。

将来ルールベースから実LLMへ差し替える場合は、`ProposalGenerator`を満たす実装を
追加して`pipeline.py`のモジュール変数を差し替えるだけで済む。
"""

from typing import Protocol

from caliboo_api.services.text_utils import find_first_match, split_sentences

from . import theme_catalog as catalog

_WEIGHT_HIGH = 2
_WEIGHT_LOW = 1

_LABEL_PROBLEM = "日報 Problem"
_LABEL_TRY = "日報 Try"
_LABEL_KEEP = "日報 Keep"
_LABEL_MOOD_COMMENT = "日報 きもち"
_LABEL_FEEDBACK = "講師フィードバック"

# 材料の並び順(日付降順のあとの、同日タイブレーク用の欄順)。
_FIELD_ORDER = {
    _LABEL_PROBLEM: 0,
    _LABEL_TRY: 1,
    _LABEL_KEEP: 2,
    _LABEL_MOOD_COMMENT: 3,
    _LABEL_FEEDBACK: 4,
}

# 「もやもや」「つかれた」に対応する日報のmood値。
_LOW_MOODS = {"foggy", "tired"}
_MOOD_MATERIAL_THRESHOLD = 3

# 直近の日報を何件まで見るか(`data/assignment_proposal_data.py`のDB問い合わせ
# 件数にもこの値を使い、定数を1か所にまとめている)。呼び出し側が既にこの件数まで
# 絞り込んで渡してくる前提のため、本モジュール側では再度スライスしない。
RECENT_REPORT_COUNT = 5


class ProposalGenerator(Protocol):
    name: str

    def generate(
        self,
        *,
        member_name: str,
        reports: list[dict],
        submission_statuses: list[str],
        feedbacks: list[dict],
        excluded_themes: set[str],
    ) -> dict: ...


def _weighted_texts(reports: list[dict], feedbacks: list[dict]) -> list[tuple[str, str, int, str]]:
    """`(text, date, weight, sourceLabel)`のリストを、日報→FBの順に組み立てる。"""
    texts: list[tuple[str, str, int, str]] = []
    for report in reports:
        texts.append((report["problem"], report["date"], _WEIGHT_HIGH, _LABEL_PROBLEM))
        texts.append((report["try"], report["date"], _WEIGHT_HIGH, _LABEL_TRY))
        texts.append((report["keep"], report["date"], _WEIGHT_LOW, _LABEL_KEEP))
        texts.append((report["moodComment"], report["date"], _WEIGHT_LOW, _LABEL_MOOD_COMMENT))
    for feedback in feedbacks:
        texts.append((feedback["comment"], feedback["date"], _WEIGHT_HIGH, _LABEL_FEEDBACK))
    return texts


def _score_and_materials(
    theme: catalog.ProposalTheme, texts: list[tuple[str, str, int, str]]
) -> tuple[int, list[dict]]:
    """テーマ1件のスコアと、一致した文から組み立てた材料候補を返す。

    !NOTE: 1つのテキスト(例: ある日の日報のProblem欄)につき最初に一致した文だけを
           採用する(`analysis.py`の`_find_evidence`と同じ考え方)。同じテキスト内の
           複数文を数えると、単に長文を書いた対象者のスコアが不当に高くなるため。
    """
    if not theme.keywords:
        return 0, []

    score = 0
    materials: list[dict] = []
    for text, date, weight, source_label in texts:
        match = find_first_match(split_sentences(text), theme.keywords)
        if match is None:
            continue
        score += weight
        kind = "feedback" if source_label == _LABEL_FEEDBACK else "report"
        materials.append({"kind": kind, "date": date, "quote": match, "sourceLabel": source_label})
    return score, materials


def _select_theme(
    texts: list[tuple[str, str, int, str]], excluded_themes: set[str]
) -> tuple[catalog.ProposalTheme, list[dict]]:
    """最高得点のテーマを選ぶ(同点はカタログ順)。候補が無ければフォールバック。

    !NOTE: `score > best_score`という厳密な不等号にすることで、カタログを先頭から
           走査したときに最初に最高点へ達したテーマがそのまま勝ち残る
           (=同点はカタログの並び順が早い方を優先する)。
    """
    best_theme: catalog.ProposalTheme | None = None
    best_score = 0
    best_materials: list[dict] = []
    for theme in catalog.THEME_CATALOG:
        if theme.key == catalog.FALLBACK_THEME_KEY or theme.key in excluded_themes:
            continue
        score, materials = _score_and_materials(theme, texts)
        if score > best_score:
            best_theme, best_score, best_materials = theme, score, materials

    if best_theme is None:
        return catalog.find_theme(catalog.FALLBACK_THEME_KEY), []
    return best_theme, best_materials


def _sort_materials(materials: list[dict]) -> list[dict]:
    """日付降順→欄順で並べ替える(いずれもソートは安定なので2段階で組み立てる)。"""
    by_field_order = sorted(
        materials, key=lambda material: _FIELD_ORDER.get(material["sourceLabel"], 99)
    )
    return sorted(by_field_order, key=lambda material: material["date"] or "", reverse=True)


def _mood_material(reports: list[dict]) -> dict | None:
    hit_count = sum(1 for report in reports if _LOW_MOODS & set(report["mood"]))
    if hit_count < _MOOD_MATERIAL_THRESHOLD:
        return None
    return {
        "kind": "mood",
        "date": None,
        "quote": f"直近{len(reports)}件の日報のうち{hit_count}件で「もやもや」「つかれた」が見られました。",
        "sourceLabel": "直近のきもち",
    }


def _progress_material(submission_statuses: list[str]) -> dict | None:
    not_submitted_count = sum(1 for status in submission_statuses if status == "not_submitted")
    if not_submitted_count == 0:
        return None
    return {
        "kind": "progress",
        "date": None,
        "quote": f"未提出の課題が{not_submitted_count}件あります。",
        "sourceLabel": "課題の進捗",
    }


def _progress_summary(submission_statuses: list[str], reports: list[dict]) -> dict:
    recent_moods = [report["mood"][0] for report in reports if report["mood"]]
    return {
        "submittedCount": sum(
            1 for status in submission_statuses if status in ("submitted", "reviewed")
        ),
        "reviewedCount": sum(1 for status in submission_statuses if status == "reviewed"),
        "notSubmittedCount": sum(
            1 for status in submission_statuses if status == "not_submitted"
        ),
        "recentMoods": recent_moods,
    }


def _build_rationale(
    member_name: str,
    theme: catalog.ProposalTheme,
    quote_materials: list[dict],
    has_mood_material: bool,
    has_progress_material: bool,
) -> str:
    if theme.key == catalog.FALLBACK_THEME_KEY and not quote_materials:
        sentences = [
            f"{member_name}さんの直近の日報から、特定のテーマに強く一致する記述は"
            "見つかりませんでした。まずは今週のふりかえりを言語化する汎用課題にしています。"
        ]
    else:
        quotes = "、".join(f"「{material['quote']}」" for material in quote_materials[:2])
        sentences = [
            f"{member_name}さんの直近の日報や講師フィードバックで{quotes}といった記述が"
            f"見られたため、「{theme.title}」をテーマに選びました。"
        ]
    if has_mood_material:
        sentences.append(
            "直近の日報で「もやもや」「つかれた」が目立つため、気持ちの面にも配慮した内容にしています。"
        )
    if has_progress_material:
        sentences.append("未提出の課題も残っているため、負担を抑えた分量にしています。")
    return "".join(sentences)


class RuleBasedProposalGenerator:
    """キーワード照合+テンプレートによる決定論的な課題案生成器。"""

    name = "rule_based_v1"

    def generate(
        self,
        *,
        member_name: str,
        reports: list[dict],
        submission_statuses: list[str],
        feedbacks: list[dict],
        excluded_themes: set[str],
    ) -> dict:
        texts = _weighted_texts(reports, feedbacks)
        theme, quote_materials = _select_theme(texts, excluded_themes)
        quote_materials = _sort_materials(quote_materials)

        mood_material = _mood_material(reports)
        progress_material = _progress_material(submission_statuses)
        materials = quote_materials.copy()
        if mood_material is not None:
            materials.append(mood_material)
        if progress_material is not None:
            materials.append(progress_material)

        rationale = _build_rationale(
            member_name,
            theme,
            quote_materials,
            mood_material is not None,
            progress_material is not None,
        )

        return {
            "themeKey": theme.key,
            "title": theme.title,
            "body": theme.body,
            "messageForMember": theme.message_for_member,
            "aim": theme.aim,
            "rationale": rationale,
            "estimateMinutes": theme.estimate_minutes,
            "materials": materials,
            "progress": _progress_summary(submission_statuses, reports),
        }
