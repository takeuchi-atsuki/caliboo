import type { QuizChoice } from "../../lib/types";

/**
 * 2a(過去問演習ドリル)から2b(質問チャット)へ画面遷移時のstateで引き継ぐ問題。
 *
 * !NOTE: 正解・解説は含めない。2aは「正解をブラウザに事前配布しない」方針
 *        (docs/screens/study.md)のため、解答前でも後でも問題文と選択肢のみを渡す。
 */
export interface QuizHandoff {
  text: string;
  choices: QuizChoice[];
}

// !NOTE: 出題は4択前提(seedの全問題が4択)。2aの選択肢ラベルと引き継ぎ文のラベルを揃えるため共有する。
export const CHOICE_LETTERS = ["A", "B", "C", "D"];

/**
 * `location.state`から引き継ぎ問題を取り出す。
 *
 * !NOTE: `location.state`はブラウザ履歴由来の任意の値が入りうるため、形状を検証し
 *        想定外の値はnullとして扱う。
 */
export function readQuizHandoff(state: unknown): QuizHandoff | null {
  if (typeof state !== "object" || state === null) return null;
  const quizQuestion = (state as { quizQuestion?: unknown }).quizQuestion;
  if (typeof quizQuestion !== "object" || quizQuestion === null) return null;
  const { text, choices } = quizQuestion as { text?: unknown; choices?: unknown };
  if (typeof text !== "string" || !Array.isArray(choices)) return null;
  if (!choices.every((choice) => typeof choice === "string" || (
    typeof choice === "object" && choice !== null && typeof choice.text === "string" &&
    typeof choice.alt === "string" && choice.alt.trim() !== "" &&
    typeof choice.imageUrl === "string" && /^\/quiz-assets\/[A-Za-z0-9_-]+\.svg$/.test(choice.imageUrl)
  ))) return null;
  return { text, choices };
}

export function buildQuizQuestionPrompt(question: QuizHandoff): string {
  const choiceLines = question.choices.map((choice, index) => `${CHOICE_LETTERS[index]}. ${typeof choice === "string" ? choice : `${choice.text}（図: ${choice.alt}）`}`);
  return ["この問題がわからない：", question.text, "", ...choiceLines].join("\n");
}


/** モデルに必要な公開本文だけを選ぶ。画像URLや採点情報は渡さない。 */
export function buildStudyQuestionContext(question: QuizHandoff) {
  return {
    text: question.text,
    choices: question.choices.map((choice) => typeof choice === "string" ? choice : `${choice.text}（図: ${choice.alt}）`),
  };
}
