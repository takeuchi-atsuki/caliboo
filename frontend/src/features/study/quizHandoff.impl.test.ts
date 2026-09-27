import { describe, it, expect } from "vitest";

import { readQuizHandoff } from "./quizHandoff";

describe("readQuizHandoff", () => {
  it("quizQuestionに問題文と選択肢を持つstateから引き継ぎ問題を取り出す", () => {
    const state = { quizQuestion: { text: "問題文", choices: ["ア", "イ"] } };

    expect(readQuizHandoff(state)).toEqual({ text: "問題文", choices: ["ア", "イ"] });
  });

  it.each([
    ["null", null],
    ["文字列", "text"],
    ["quizQuestionなし", {}],
    ["quizQuestionがnull", { quizQuestion: null }],
    ["textが文字列でない", { quizQuestion: { text: 1, choices: [] } }],
    ["choicesが配列でない", { quizQuestion: { text: "問題文", choices: "ア" } }],
    ["choicesに文字列以外を含む", { quizQuestion: { text: "問題文", choices: ["ア", 2] } }],
  ])("想定外の形状(%s)はnullを返す", (_label, state) => {
    expect(readQuizHandoff(state)).toBeNull();
  });
});
