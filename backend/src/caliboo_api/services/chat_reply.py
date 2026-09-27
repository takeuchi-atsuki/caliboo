import itertools

from caliboo_api.schemas.common import ChatMessage, ChatReference

_ojt_id_counter = itertools.count(1)
_study_id_counter = itertools.count(1)


def build_ojt_reply(dept_name: str, question_text: str) -> ChatMessage:
    """OJTメンターのダミー回答を生成する。

    !NOTE: 実際のLLM連携は未実装のため、質問文をそのままテンプレートに
           埋め込むだけの固定応答にしている。ナレッジ検索を実装する際は
           この関数の内部だけを差し替えれば良いように、呼び出し側からは
           質問文と課名のみを受け取るインターフェースにしている。
    """
    reply_id = f"ojt-reply-{next(_ojt_id_counter)}"
    text = f"{dept_name}のナレッジによると、「{question_text}」については社内資料に手順がまとまっています。"
    return ChatMessage(
        id=reply_id,
        role="bot",
        text=text,
        references=[ChatReference(label=f"{dept_name} ナレッジ資料")],
    )


def build_study_reply(question_text: str) -> ChatMessage:
    """学習サポートAIのダミー回答を生成する。"""
    reply_id = f"study-reply-{next(_study_id_counter)}"
    text = (
        f"いい質問！「{question_text}」について解説するね。"
        "ポイントは3つ。①定義を押さえる ②具体例で確認する ③関連する過去問で練習する、だよ。"
    )
    return ChatMessage(id=reply_id, role="bot", text=text)
