import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../../lib/apiClient";
import { useHomeSummary } from "./useHomeSummary";
vi.mock("../../lib/apiClient", () => ({ apiClient: { get: vi.fn() } }));
beforeEach(() => vi.resetAllMocks());
describe("ホーム取得", () => {
  it("結果を返す", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ strengths: [] });
    const { result } = renderHook(useHomeSummary);
    await waitFor(() => expect(result.current.summary).toEqual({ strengths: [] }));
  });
  it("失敗を表示する", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("offline"));
    const { result } = renderHook(useHomeSummary);
    await waitFor(() => expect(result.current.error).toContain("読み込みに失敗"));
  });
  it.each([false, true])("アンマウント後の応答を破棄する %s", async (failed) => {
    let finish!: (value: unknown) => void;
    vi.mocked(apiClient.get).mockImplementation(() => new Promise((resolve, reject) => { finish = failed ? reject : resolve; }));
    const { unmount } = renderHook(useHomeSummary);
    unmount();
    await act(async () => finish(failed ? new Error("late") : {}));
  });
});
