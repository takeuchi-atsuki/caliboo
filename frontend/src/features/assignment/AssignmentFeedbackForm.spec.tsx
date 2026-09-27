import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { AssignmentFeedbackForm } from "./AssignmentFeedbackForm";
it("未提出にはフィードバックできない", () => {
  render(<AssignmentFeedbackForm assignmentId={1} status="not_submitted" submission={null} submitting={false} onSubmit={vi.fn()} />);
  expect(screen.getByText(/まだ回答が提出/)).toBeInTheDocument();
});
it("任意点数の範囲と更新", () => {
  const submit = vi.fn();
  const submission = { answerText: "回答", submittedAt: "today", feedbackComment: "良い", score: 80 };
  const { rerender } = render(<AssignmentFeedbackForm assignmentId={1} status="reviewed" submission={submission} submitting={false} onSubmit={submit} />);
  const button = screen.getByRole("button", { name: "フィードバックを更新する" });
  const score = screen.getByLabelText("点数（任意・0〜100）");
  for (const invalid of ["-1", "101", "1.5"]) {
    fireEvent.change(score, { target: { value: invalid } });
    expect(button).toBeDisabled();
  }
  fireEvent.change(score, { target: { value: "100" } });
  fireEvent.change(screen.getByPlaceholderText("回答へのコメントを記入してください"), { target: { value: "更新" } });
  fireEvent.click(button);
  expect(submit).toHaveBeenCalledWith("更新", 100);
  fireEvent.change(score, { target: { value: "" } });
  fireEvent.click(button);
  expect(submit).toHaveBeenCalledWith("更新", null);
  rerender(<AssignmentFeedbackForm assignmentId={2} status="submitted" submission={null} submitting onSubmit={submit} />);
  expect(screen.getByRole("button", { name: "フィードバックを送る" })).toBeDisabled();
});
