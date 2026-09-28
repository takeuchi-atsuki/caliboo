import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { QuizPracticeReason } from "./QuizPracticeReason";

it.each([
  ["mistake_review", "誤答の復習"], ["scheduled_review", "復習のタイミング"], ["new", "新しい問題"],
  ["practice", "練習"], [undefined, "練習"],
] as const)("出題理由を表示する %s", (reason, label) => {
  render(<QuizPracticeReason reason={reason} />);
  expect(screen.getByText(new RegExp(label))).toBeInTheDocument();
});
