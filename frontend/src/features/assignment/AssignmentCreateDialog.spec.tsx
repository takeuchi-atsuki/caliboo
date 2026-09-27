import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { AssignmentCreateDialog } from "./AssignmentCreateDialog";
import { useResource } from "../../lib/useResource";
vi.mock("../../lib/useResource", () => ({ useResource: vi.fn() }));
beforeEach(() => vi.mocked(useResource).mockReturnValue({ data: { users: [
  { id: 2, displayName: "ソラ", role: "member", active: true },
  { id: 3, displayName: "講師", role: "admin", active: true },
  { id: 4, displayName: "無効", role: "member", active: false },
] }, error: null, busy: false, reload: vi.fn(), act: vi.fn() }));
it.each([true, false])("個人宛て課題の作成と失敗時の保持 %s", async (success) => {
  const create = vi.fn().mockResolvedValue(success);
  const close = vi.fn();
  render(<AssignmentCreateDialog open onClose={close} submitting={false} onCreate={create} />);
  fireEvent.change(screen.getByPlaceholderText("例: ビジネスメールの書き方をまとめよう"), { target: { value: "課題" } });
  fireEvent.change(screen.getByPlaceholderText("課題の内容を記入してください"), { target: { value: "本文" } });
  fireEvent.mouseDown(screen.getByLabelText("配信先"));
  fireEvent.click(screen.getByRole("option", { name: "ソラ" }));
  fireEvent.click(screen.getByRole("button", { name: "作成する" }));
  await waitFor(() => expect(create).toHaveBeenCalledWith("課題", "本文", 2));
  if (success) await waitFor(() => expect(close).toHaveBeenCalled());
  else expect(screen.getByDisplayValue("課題")).toBeInTheDocument();
});
it("全員宛てと未取得の選択肢", async () => {
  vi.mocked(useResource).mockReturnValue({ data: null, error: null, busy: false, reload: vi.fn(), act: vi.fn() });
  const create = vi.fn().mockResolvedValue(true);
  const { rerender } = render(<AssignmentCreateDialog open={false} onClose={vi.fn()} submitting onCreate={create} />);
  rerender(<AssignmentCreateDialog open onClose={vi.fn()} submitting={false} onCreate={create} />);
  expect(screen.getByRole("button", { name: "作成する" })).toBeDisabled();
  fireEvent.change(screen.getByPlaceholderText("例: ビジネスメールの書き方をまとめよう"), { target: { value: "課題" } });
  fireEvent.change(screen.getByPlaceholderText("課題の内容を記入してください"), { target: { value: "本文" } });
  fireEvent.click(screen.getByRole("button", { name: "作成する" }));
  await waitFor(() => expect(create).toHaveBeenCalledWith("課題", "本文", undefined));
});
