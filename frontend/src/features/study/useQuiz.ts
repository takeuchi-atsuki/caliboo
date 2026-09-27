import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "../../lib/apiClient";
import type { ProgressCategory, QuizAnswerResponse, QuizCategory, QuizQuestion, StudyProgress } from "../../lib/types";

export function useQuiz() {
  const [progress, setProgress] = useState<StudyProgress | null>(null);
  const [question, setQuestion] = useState<QuizQuestion | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<QuizCategory | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [result, setResult] = useState<QuizAnswerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const version = useRef(0);
  const submittingRef = useRef(false);
  const loadNextQuestion = useCallback(async (category: QuizCategory | null, excludeId?: string) => {
    const current = ++version.current;
    setSelectedIndex(null); setResult(null); setQuestion(null); setError(null);
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (excludeId) params.set("excludeId", excludeId);
    const query = params.toString() ? `?${params.toString()}` : "";
    try {
      const next = await apiClient.get<QuizQuestion>(`/api/quiz/next${query}`);
      if (current === version.current) setQuestion(next);
    } catch {
      if (current === version.current) setError("問題を取得できませんでした。もう一度お試しください。");
    }
  }, []);
  useEffect(() => {
    let cancelled = false;
    apiClient.get<StudyProgress>("/api/study/progress").then((data) => {
      if (!cancelled) setProgress(data);
    }).catch(() => { if (!cancelled) setError("進捗を取得できませんでした。"); });
    void loadNextQuestion(null);
    return () => { cancelled = true; version.current++; };
  }, [loadNextQuestion]);
  const selectCategory = (category: ProgressCategory["id"]) => {
    setCategoryFilter(category);
    void loadNextQuestion(category, question?.id);
  };
  const selectChoice = (index: number) => {
    if (!result && !submittingRef.current) setSelectedIndex(index);
  };
  const submitAnswer = async () => {
    if (!question || selectedIndex === null || result || submittingRef.current) return;
    const current = version.current;
    submittingRef.current = true; setSubmitting(true); setError(null);
    try {
      const answer = await apiClient.post<QuizAnswerResponse>("/api/quiz/answer", {
        questionId: question.id, selectedIndex,
      });
      if (current !== version.current) return;
      setResult(answer);
      const latest = await apiClient.get<StudyProgress>("/api/study/progress");
      if (current === version.current) setProgress(latest);
    } catch {
      if (current === version.current) setError("回答・進捗の更新に失敗しました。再読み込みしてください。");
    } finally { submittingRef.current = false; setSubmitting(false); }
  };
  return { progress, question, categoryFilter, selectedIndex, result, error, submitting,
    selectCategory, selectChoice, submitAnswer,
    nextQuestion: () => loadNextQuestion(categoryFilter, question?.id) };
}
