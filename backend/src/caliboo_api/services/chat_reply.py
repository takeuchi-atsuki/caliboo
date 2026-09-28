import itertools

from caliboo_api.schemas.common import ChatMessage

_study_id_counter = itertools.count(1)


def build_study_reply(question_text: str) -> ChatMessage:
    """学習サポートAIのダミー回答を生成する。"""
    reply_id = f"study-reply-{next(_study_id_counter)}"
    text = (
        f"いい質問！「{question_text}」について解説するね。"
        "ポイントは3つ。①定義を押さえる ②具体例で確認する ③関連する過去問で練習する、だよ。"
    )
    return ChatMessage(id=reply_id, role="bot", text=text)
