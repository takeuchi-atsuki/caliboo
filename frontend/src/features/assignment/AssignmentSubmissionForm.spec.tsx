import { expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { AssignmentDetail } from "../../lib/types";
import { AssignmentSubmissionForm } from "./AssignmentSubmissionForm";

const assignment: AssignmentDetail = {
  id: 10, title: "課題", body: "説明", status: "not_submitted", createdAt: "2026-10-03",
  target: null, messageForMember: null,
};

it("ワークスペースのコードを回答欄へ反映し、提出できる", () => {
  const submit = vi.fn().mockResolvedValue(undefined);
  const { rerender } = render(<AssignmentSubmissionForm assignment={assignment} submitting={false} onSubmit={submit} />);
  rerender(<AssignmentSubmissionForm assignment={assignment} submitting={false} onSubmit={submit}
    workspaceAnswer={{ text: "console.log('ok')", revision: 1 }} />);
  expect(screen.getByPlaceholderText("ここに回答を記入してください")).toHaveValue("console.log('ok')");
  fireEvent.click(screen.getByRole("button", { name: "提出する" }));
  expect(submit).toHaveBeenCalledWith("console.log('ok')");
});
