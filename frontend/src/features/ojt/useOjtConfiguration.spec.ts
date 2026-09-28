import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { apiClient, ApiError } from "../../lib/apiClient";
import type { OjtConfiguration } from "../../lib/types";
import { useOjtConfiguration } from "./useOjtConfiguration";

vi.mock("../../lib/apiClient", async (original) => ({
  ...await original<typeof import("../../lib/apiClient")>(),
  apiClient: { get: vi.fn(), post: vi.fn() },
}));
const configuration: OjtConfiguration = {
  id: "dev", name: "開発課", icon: "ph ph-code", color: "#d6ebff", welcomeMessage: "案内",
  quickAsks: ["開発の質問"], replyGuidance: "補足", knowledge: [], revision: 3,
};
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(apiClient.get).mockResolvedValue(configuration);
  vi.mocked(apiClient.post).mockResolvedValue({ ...configuration, revision: 4 });
});

it("部署の設定を取得し、更新番号を送信して保存する", async () => {
  const { result } = renderHook(() => useOjtConfiguration("dev"));
  expect(result.current.loading).toBe(true);
  await act(async () => { expect(await result.current.save()).toBeNull(); });
  await waitFor(() => expect(result.current.draft).toEqual(configuration));
  act(() => result.current.setDraft({ ...configuration, name: "変更した名前" }));
  await act(async () => result.current.save());
  expect(apiClient.post).toHaveBeenCalledWith("/api/ojt/departments/dev/configuration", {
    name: "変更した名前", icon: "ph ph-code", color: "#d6ebff", welcomeMessage: "案内",
    quickAsks: ["開発の質問"], replyGuidance: "補足", knowledge: [], revision: 3,
  });
  expect(result.current.draft?.revision).toBe(4);
  expect(result.current.saved).toBe(true);
  expect(result.current.saving).toBe(false);
});

it("新規設定はIDを指定し更新番号なしで作成する", async () => {
  const { result } = renderHook(() => useOjtConfiguration(""));
  expect(apiClient.get).not.toHaveBeenCalled();
  expect(result.current.draft?.quickAsks).toEqual([]);
  act(() => result.current.setDraft({ ...configuration, id: "research", revision: 0 }));
  await act(async () => result.current.save());
  const sent = vi.mocked(apiClient.post).mock.calls[0];
  expect(sent[0]).toBe("/api/ojt/departments");
  expect(sent[1]).toMatchObject({ id: "research" });
  expect(sent[1]).not.toHaveProperty("revision");
});

it.each(["dev", ""])("競合・重複時は入力を保持し理由を表示 (%s)", async (id) => {
  const { result } = renderHook(() => useOjtConfiguration(id));
  await waitFor(() => expect(result.current.draft).not.toBeNull());
  act(() => result.current.setDraft({ ...configuration, name: "保存前の入力" }));
  vi.mocked(apiClient.post).mockRejectedValue(new ApiError(409, "conflict"));
  await act(async () => { expect(await result.current.save()).toBeNull(); });
  expect(result.current.draft?.name).toBe("保存前の入力");
  expect(result.current.error).toContain(id ? "他の講師" : "部署ID");
  expect(result.current.saved).toBe(false);
  await act(async () => result.current.reload());
  expect(result.current.error).toBeNull();
  expect(result.current.draft?.name).toBe(id ? "開発課" : "");
});

it.each([new Error("network"), new ApiError(422, "invalid")])("通信・入力エラーでも入力を保持", async (reason) => {
  const { result } = renderHook(() => useOjtConfiguration("dev"));
  await waitFor(() => expect(result.current.draft).toEqual(configuration));
  vi.mocked(apiClient.post).mockRejectedValue(reason);
  await act(async () => result.current.save());
  expect(result.current.draft).toEqual(configuration);
  expect(result.current.error).toContain("入力内容と接続");
});

it("読み込み失敗を表示し、再取得できる", async () => {
  vi.mocked(apiClient.get).mockRejectedValueOnce(new Error());
  const { result } = renderHook(() => useOjtConfiguration("dev"));
  await waitFor(() => expect(result.current.error).toContain("取得"));
  expect(result.current.loading).toBe(false);
  expect(result.current.draft).toBeNull();
  await act(async () => result.current.reload());
  expect(result.current.draft).toEqual(configuration);
});

it.each([false, true])("部署切替後に古い取得応答が到着しても無視 (%s)", async (failed) => {
  let finish!: (value: unknown) => void;
  vi.mocked(apiClient.get).mockImplementationOnce(() => new Promise((resolve, reject) => { finish = failed ? reject : resolve; }));
  const { result, rerender } = renderHook(({ id }) => useOjtConfiguration(id), { initialProps: { id: "dev" } });
  rerender({ id: "" });
  await act(async () => finish(failed ? new Error() : configuration));
  expect(result.current.draft?.id).toBe("");
  expect(result.current.error).toBeNull();
  expect(result.current.loading).toBe(false);
});

it.each([false, true])("二重保存を防止し、部署切替後の保存応答を無視 (%s)", async (failed) => {
  const { result, rerender } = renderHook(({ id }) => useOjtConfiguration(id), { initialProps: { id: "dev" } });
  await waitFor(() => expect(result.current.draft).toEqual(configuration));
  let finish!: (value: unknown) => void;
  vi.mocked(apiClient.post).mockImplementationOnce(() => new Promise((resolve, reject) => { finish = failed ? reject : resolve; }));
  let pending!: Promise<unknown>;
  act(() => { pending = result.current.save(); });
  await act(async () => { expect(await result.current.save()).toBeNull(); });
  expect(apiClient.post).toHaveBeenCalledTimes(1);
  expect(result.current.saving).toBe(true);
  rerender({ id: "" });
  await act(async () => { finish(failed ? new Error() : configuration); await pending; });
  expect(result.current.draft?.id).toBe("");
  expect(result.current.saved).toBe(false);
  expect(result.current.error).toBeNull();
});
