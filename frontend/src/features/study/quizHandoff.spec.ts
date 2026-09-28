import { describe, it, expect } from "vitest";

import { buildQuizQuestionPrompt, buildStudyQuestionContext } from "./quizHandoff";

describe("buildQuizQuestionPrompt", () => {
  it("問題文と、A〜Dのラベルを付けた選択肢を改行区切りで並べる", () => {
    const prompt = buildQuizQuestionPrompt({ text: "問題文", choices: ["ア", "イ", "ウ", "エ"] });

    expect(prompt).toBe("この問題がわからない：\n問題文\n\nA. ア\nB. イ\nC. ウ\nD. エ");
  });
});

it("生成用文脈は公開本文と代替文だけを選ぶ", () => {
  const question = { text: "図を選ぶ", choices: ["文字の選択肢", { text: "波形", alt: "上下する図", imageUrl: "/quiz-assets/a.svg" }], correctIndex: 1, explanation: "答え" };
  expect(buildStudyQuestionContext(question)).toEqual({ text: "図を選ぶ", choices: ["文字の選択肢", "波形（図: 上下する図）"] });
});
