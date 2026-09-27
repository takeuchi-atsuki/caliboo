"""3職種レビューのFan-in統合(ルールベース)。

!NOTE: 仕様書§3は統合方式として「ルールベース or 軽量LLM」を許容している。
       確信度算出と同様に決定論性を優先し、LLMを介さないルールベース実装にする。
"""

REVIEWER_LABELS = {
    "alpha": "管理職(MELCHIOR)",
    "beta": "講師(BALTHASAR)",
    "gamma": "シニアエンジニア(CASPER)",
}


def merge_reviews(reviews: list[dict]) -> dict:
    """3件のレビューコメントを1つの統合コメント・フラグ一覧にまとめる。

    戻り値は`{"fanInComment": str, "fanInFlags": list[str]}`。
    """
    sections = []
    flags: list[str] = []
    for review in reviews:
        label = REVIEWER_LABELS.get(review["agentKey"], review["reviewerRole"])
        sections.append(f"[{label}] {review['comment']}")
        for flag in review["flags"]:
            if flag not in flags:
                flags.append(flag)

    fan_in_comment = "\n".join(sections)
    return {"fanInComment": fan_in_comment, "fanInFlags": flags}
