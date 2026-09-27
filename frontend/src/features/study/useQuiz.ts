import { useCallback, useEffect, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import type { ProgressCategory, QuizAnswerResponse, QuizCategory, QuizQuestion, StudyProgress } from "../../lib/types";

export function useQuiz() {
  const [progress, setProgress] = useState<StudyProgress | null>(null);
  const [question, setQuestion] = useState<QuizQuestion | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<QuizCategory | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [result, setResult] = useState<QuizAnswerResponse | null>(null);

  const loadNextQuestion = useCallback(async (category: QuizCategory | null, excludeId?: string) => {
    setSelectedIndex(null);
    setResult(null);
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (excludeId) params.set("excludeId", excludeId);
    const query = params.toString() ? `?${params.toString()}` : "";
    const next = await apiClient.get<QuizQuestion>(`/api/quiz/next${query}`);
    setQuestion(next);
  }, []);

  useEffect(() => {
    apiClient.get<StudyProgress>("/api/study/progress").then(setProgress);
    loadNextQuestion(null);
  }, [loadNextQuestion]);

  const selectCategory = (category: ProgressCategory["id"]) => {
    setCategoryFilter(category);
    loadNextQuestion(category, question?.id);
  };

  const selectChoice = (index: number) => {
    if (result) return;
    setSelectedIndex(index);
  };

  const submitAnswer = async () => {
    if (!question || selectedIndex === null) return;
    const answer = await apiClient.post<QuizAnswerResponse>("/api/quiz/answer", {
      questionId: question.id,
      selectedIndex,
    });
    setResult(answer);
  };

  const nextQuestion = () => loadNextQuestion(categoryFilter, question?.id);

  return {
    progress,
    question,
    categoryFilter,
    selectedIndex,
    result,
    selectCategory,
    selectChoice,
    submitAnswer,
    nextQuestion,
  };
}
