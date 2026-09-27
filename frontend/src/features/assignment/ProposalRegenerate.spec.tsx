import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ProposalRegenerate } from "./ProposalRegenerate";
import { useResource } from "../../lib/useResource";
vi.mock("../../lib/useResource", () => ({ useResource: vi.fn() }));
it.each([true, false])("指示による再生成・履歴の表示 %s", async (success) => {
  const act = vi.fn().mockResolvedValue(success);
  vi.mocked(useResource).mockReturnValue({ data: { revisions: [{ id: 1, instruction: "前回", previous: { title: "元", body: "旧本文" } }] }, error: null, busy: false, reload: vi.fn(), act });
  const { rerender } = render(<ProposalRegenerate proposalId={1} pending generator="rules" />);
  fireEvent.change(screen.getByLabelText("AIに調整を頼む"), { target: { value: "短く" } });
  fireEvent.click(screen.getByRole("button", { name: "作り直しを依頼" }));
  await waitFor(() => expect(act).toHaveBeenCalledWith("/api/assignment-proposals/1/regenerate", { instruction: "短く" }));
  if (success) await screen.findByText(/再生成を依頼しました/);
  else expect(screen.queryByText(/再生成を依頼しました/)).not.toBeInTheDocument();
  vi.mocked(useResource).mockReturnValue({ data: null, error: "失敗", busy: true, reload: vi.fn(), act });
  rerender(<ProposalRegenerate proposalId={1} pending={false} generator="codex_agent:test" />);
  expect(screen.getByText("生成元: エージェント")).toBeInTheDocument();
  expect(screen.getByText("失敗")).toBeInTheDocument();
});
