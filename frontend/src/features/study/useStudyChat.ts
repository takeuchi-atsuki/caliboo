import { useCallback, useEffect, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import type { ChatMessage, RelatedQuestionItem } from "../../lib/types";
import { QUIZ_HANDOFF_REPLY, buildQuizQuestionPrompt, type QuizHandoff } from "./quizHandoff";

const QUICK_QUESTIONS = ["この分野の頻出ポイントは？", "覚え方のコツを教えて", "類題を出して"];

const INITIAL_MESSAGE: ChatMessage = {
  id: "study-initial",
  role: "bot",
  text: "資格試験について気軽に質問してね。過去問の解き方や用語の意味、なんでも聞いてOK！",
  references: [],
};

/**
 * 2b(質問チャット)のロジック。
 *
 * @param handoff 2aから引き継いだ問題。指定時は問題文を自分の質問として表示し、
 *                モック回答(QUIZ_HANDOFF_REPLY)を続けて表示する。
 *
 * !NOTE: 引き継ぎメッセージはeffectで追加せずuseStateの初期値にしている。StrictModeの
 *        二重effect実行や、呼び出し側がlocation.stateを消した後の再レンダーで
 *        二重追加されないようにするため。
 */
export function useStudyChat(handoff: QuizHandoff | null = null) {
  const [relatedQuestions, setRelatedQuestions] = useState<RelatedQuestionItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    handoff
      ? [
          INITIAL_MESSAGE,
          { id: "study-handoff-question", role: "me", text: buildQuizQuestionPrompt(handoff), references: [] },
          QUIZ_HANDOFF_REPLY,
        ]
      : [INITIAL_MESSAGE],
  );
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    apiClient
      .get<{ items: RelatedQuestionItem[] }>("/api/study/related-questions")
      .then((data) => setRelatedQuestions(data.items));
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;
    const myMessage: ChatMessage = {
      id: `local-${Date.now()}-${Math.random()}`,
      role: "me",
      text,
      references: [],
    };
    setMessages((prev) => [...prev, myMessage]);
    setInput("");
    setSending(true);
    try {
      const reply = await apiClient.post<ChatMessage>("/api/study/chat", { text });
      setMessages((prev) => [...prev, reply]);
    } finally {
      setSending(false);
    }
  }, []);

  return {
    relatedQuestions,
    messages,
    input,
    setInput,
    sending,
    sendMessage,
    quickQuestions: QUICK_QUESTIONS,
  };
}
