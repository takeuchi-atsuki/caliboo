import { describe, it, expect } from "vitest";

import { buildQuizQuestionPrompt } from "./quizHandoff";

describe("buildQuizQuestionPrompt", () => {
  it("問題文と、A〜Dのラベルを付けた選択肢を改行区切りで並べる", () => {
    const prompt = buildQuizQuestionPrompt({ text: "問題文", choices: ["ア", "イ", "ウ", "エ"] });

    expect(prompt).toBe("この問題がわからない：\n問題文\n\nA. ア\nB. イ\nC. ウ\nD. エ");
  });
});
