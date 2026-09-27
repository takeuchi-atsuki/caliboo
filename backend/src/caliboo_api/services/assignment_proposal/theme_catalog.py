"""課題案生成で使うテーマカタログ。

!NOTE: `FALLBACK_THEME_KEY`のテーマはキーワードを持たない(常にスコア0)。日報・
       フィードバックがどのテーマにも当てはまらない場合の最後の受け皿として扱うため、
       他のテーマと異なり過去に配信・見送り済みでも除外しない(`providers.py`参照)。

!NOTE: `keywords`はこのモジュールを書いた時点のキーワードで固定し、シードデータ
       (`data/seed/report_seed.py`)側をこれに合わせて書く。逆にシードの文言に
       合わせてキーワードを足すと、シード専用のトートロジーになり「意図した日報の
       内容に合うテーマが選ばれるか」の検証にならなくなるため。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProposalTheme:
    """課題案テーマ1件と、日報・フィードバックから検出するためのキーワード。"""

    key: str
    keywords: tuple[str, ...]
    title: str
    body: str
    message_for_member: str
    aim: str
    estimate_minutes: int


FALLBACK_THEME_KEY = "fallback_reflection"

THEME_CATALOG: tuple[ProposalTheme, ...] = (
    ProposalTheme(
        key="report_structure",
        keywords=("報告", "結論", "要点", "聞き返", "分かりにくい", "分かりづらい", "伝わ"),
        title="報告の構成を整理してみよう",
        body=(
            "直近の日報で、報告の要点が伝わりにくかった様子が見られます。"
            "「結論→理由→詳細」の順番を意識して、200字程度で要点をまとめる練習を"
            "してみましょう。"
        ),
        message_for_member="報告の組み立て方を一緒に練習してみましょう。",
        aim="結論から伝える報告の型を身につける",
        estimate_minutes=30,
    ),
    ProposalTheme(
        key="sql_join",
        keywords=("JOIN", "結合", "SQL", "クエリ", "テーブル"),
        title="テーブル結合(JOIN)を復習しよう",
        body=(
            "SQLのテーブル結合(JOIN)で戸惑った様子が見られます。INNER JOINと"
            "LEFT JOINの違いを整理し、簡単なサンプルテーブルで結合結果を"
            "確認してみましょう。"
        ),
        message_for_member="JOINの基本を一緒に復習しましょう。",
        aim="テーブル結合の基本パターンを理解する",
        estimate_minutes=40,
    ),
    ProposalTheme(
        key="feedback_acceptance",
        keywords=("指摘", "レビュー", "落ち込", "ミス", "指導"),
        title="指摘を次に活かす振り返りをしよう",
        body=(
            "レビューでの指摘を受けて落ち込んだ様子が見られます。指摘された点と、"
            "次にどう活かすかを箇条書きで整理してみましょう。"
        ),
        message_for_member="指摘を次にどう活かすか、一緒に整理しましょう。",
        aim="指摘を建設的に受け止め、次の行動に変える",
        estimate_minutes=20,
    ),
    ProposalTheme(
        key="git_workflow",
        keywords=("Git", "ブランチ", "プルリクエスト", "マージ", "コミット"),
        title="Gitのブランチ運用を整理しよう",
        body=(
            "Gitのブランチ運用で戸惑った様子が見られます。featureブランチの作成から"
            "レビュー、mainへのマージまでの流れを、自分の言葉で説明できるように"
            "まとめてみましょう。"
        ),
        message_for_member="ブランチ運用の流れを一緒に整理しましょう。",
        aim="Gitのブランチ運用フローを理解する",
        estimate_minutes=30,
    ),
    ProposalTheme(
        key="meeting_terms",
        keywords=("会議", "用語", "専門用語", "略語", "打ち合わせ"),
        title="会議で出てきた用語を整理しよう",
        body=(
            "会議で専門用語が分からず戸惑った様子が見られます。分からなかった用語を"
            "リストアップし、意味を調べてまとめてみましょう。"
        ),
        message_for_member="会議で出てきた用語を一緒に整理しましょう。",
        aim="会議で使われる専門用語への理解を深める",
        estimate_minutes=20,
    ),
    ProposalTheme(
        key=FALLBACK_THEME_KEY,
        keywords=(),
        title="今週の振り返りをまとめよう",
        body=(
            "今週取り組んだことと来週試したいことを、「Keep・Problem・Try」の形で"
            "200字程度にまとめてみましょう。"
        ),
        message_for_member="気軽に今の状況を教えてください。",
        aim="自分の状況を言語化し、次の行動につなげる",
        estimate_minutes=15,
    ),
)


def find_theme(key: str) -> ProposalTheme:
    """テーマキーから定義を引く。未知のキーは`KeyError`。"""
    for theme in THEME_CATALOG:
        if theme.key == key:
            return theme
    raise KeyError(key)
