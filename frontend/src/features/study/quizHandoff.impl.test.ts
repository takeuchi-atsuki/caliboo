import { describe, it, expect } from "vitest";

import { buildQuizQuestionPrompt, readQuizHandoff } from "./quizHandoff";

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

it("画像選択肢は代替文を引き継ぎ、外部URLと不正な形を拒否する", () => {
  const image = { text: "波形", imageUrl: "/quiz-assets/wave-a.svg", alt: "上下する波形" };
  const state = { quizQuestion: { text: "図を選ぶ", choices: [image] } };
  expect(readQuizHandoff(state)).toEqual(state.quizQuestion);
  expect(buildQuizQuestionPrompt(state.quizQuestion)).toContain("上下する波形");
  for (const choice of [null, {}, { ...image, text: 3 }, { ...image, alt: 3 }, { ...image, alt: " " },
    { ...image, imageUrl: 1 }, { ...image, imageUrl: "https://example.com/a.svg" }]) {
    expect(readQuizHandoff({ quizQuestion: { text: "図", choices: [choice] } })).toBeNull();
  }
});
