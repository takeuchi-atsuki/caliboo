"""複数の解析処理から共用するテキスト分割・キーワード照合ユーティリティ。

!NOTE: 元は`services/poc_strength/analysis.py`だけが持っていた実装だが、課題案生成
       (`services/assignment_proposal/providers.py`)も同じ「文分割+部分一致」で
       根拠を採点・引用するため、共通モジュールへ切り出した。句点(。)で区切るだけの
       単純な実装だが、両者が同じ分割規則・一致判定を使うことを保証する。
"""

import re


def split_sentences(text: str) -> list[str]:
    """文字列を句点(。)区切りの文リストに分割する。句点が無ければ全体を1文として返す。"""
    sentences = [sentence for sentence in re.split(r"(?<=。)", text) if sentence.strip()]
    return sentences or [text]


def find_first_match(sentences: list[str], keywords: tuple[str, ...]) -> str | None:
    """`sentences`のうち、`keywords`のいずれかを含む最初の文を返す(無ければ`None`)。"""
    for sentence in sentences:
        if any(keyword in sentence for keyword in keywords):
            return sentence.strip()
    return None
