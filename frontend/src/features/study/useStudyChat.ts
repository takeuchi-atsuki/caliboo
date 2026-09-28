import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import type { ChatMessage, RelatedQuestionItem } from "../../lib/types";
import { buildQuizQuestionPrompt, buildStudyQuestionContext, type QuizHandoff } from "./quizHandoff";

const QUICK_QUESTIONS = ["この分野の頻出ポイントは？", "覚え方のコツを教えて", "類題を出して"];
const INITIAL_MESSAGE: ChatMessage = {
  id: "study-initial", role: "bot",
  text: "資格試験について気軽に質問してね。問題の条件や用語を一緒に整理しましょう。",
  references: [],
};
type Turn = Pick<ChatMessage, "role" | "text">;
type FailedRequest = { text: string; initial: boolean };

export function useStudyChat(handoff: QuizHandoff | null = null) {
  // !NOTE: location.state消去後も、同じ会話では公開問題を文脈として維持する。
  const initialQuestion = useRef(handoff);
  const [relatedQuestions, setRelatedQuestions] = useState<RelatedQuestionItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>(() => handoff ? [
    INITIAL_MESSAGE,
    { id: "study-handoff-question", role: "me", text: buildQuizQuestionPrompt(handoff), references: [] },
  ] : [INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [relatedError, setRelatedError] = useState<string | null>(null);
  const [failed, setFailed] = useState<FailedRequest | null>(null);
  const sendingRef = useRef(false);
  const mounted = useRef(false);
  const started = useRef(false);
  const history = useRef<Turn[]>([]);

  const sendMessage = useCallback(async (text: string, initial = false) => {
    if (!text.trim() || sendingRef.current || !mounted.current) return;
    sendingRef.current = true;
    setSending(true); setError(null); setFailed(null);
    if (!initial) setInput(text);
    try {
      const question = initialQuestion.current;
      const reply = await apiClient.post<ChatMessage>("/api/study/chat", {
        text, history: history.current.slice(-12),
        ...(question ? { question: buildStudyQuestionContext(question) } : {}),
      });
      if (!mounted.current) return;
      history.current = history.current.concat({ role: "me", text }, { role: "bot", text: reply.text }).slice(-12);
      const mine: ChatMessage = { id: `${reply.id}-me`, role: "me", text, references: [] };
      setMessages((previous) => [...previous, ...(initial ? [] : [mine]), reply]);
      if (!initial) setInput((current) => current === text ? "" : current);
    } catch {
      if (mounted.current) {
        setError("回答を取得できませんでした。入力を確認して再送してください。");
        setFailed({ text, initial });
      }
    } finally {
      sendingRef.current = false;
      if (mounted.current) setSending(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    let active = true;
    apiClient.get<{ items: RelatedQuestionItem[] }>("/api/study/related-questions")
      .then((data) => { if (active) setRelatedQuestions(data.items); })
      .catch(() => { if (active) setRelatedError("関連する過去問を取得できませんでした。質問は送信できます。"); });
    // !NOTE: StrictModeのeffect再実行で問題を二重送信しない。未完了の1件を同じrefで追跡する。
    if (initialQuestion.current && !started.current) {
      started.current = true;
      void sendMessage("この問題の考え方を教えてください。", true);
    }
    return () => { active = false; mounted.current = false; };
  }, [sendMessage]);

  const retry = () => failed ? sendMessage(failed.initial ? failed.text : input, failed.initial) : Promise.resolve();
  return { relatedQuestions, relatedError, messages, input, setInput, sending, error,
    canRetry: failed !== null, retry, sendMessage, quickQuestions: QUICK_QUESTIONS };
}
