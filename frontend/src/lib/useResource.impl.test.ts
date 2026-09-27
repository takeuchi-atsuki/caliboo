import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { apiClient } from "./apiClient";
import { useResource } from "./useResource";
vi.mock("./apiClient", () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => vi.resetAllMocks());
it("未選択・取得・操作・再取得", async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ value: 1 });
  const { result, rerender } = renderHook(({ path }) => useResource(path), { initialProps: { path: null as string | null } });
  expect(apiClient.get).not.toHaveBeenCalled();
  rerender({ path: "/items" });
  await waitFor(() => expect(result.current.data).toEqual({ value: 1 }));
  vi.mocked(apiClient.post).mockResolvedValue({});
  await act(async () => expect(await result.current.act("/items", {})).toBe(true));
  expect(result.current.busy).toBe(false);
});
it("取得・保存エラー", async () => {
  vi.mocked(apiClient.get).mockRejectedValue(new Error());
  const { result } = renderHook(() => useResource("/items"));
  await waitFor(() => expect(result.current.error).toContain("読み込み"));
  vi.mocked(apiClient.post).mockRejectedValue(new Error());
  await act(async () => expect(await result.current.act("/items", {})).toBe(false));
  expect(result.current.error).toContain("保存");
});
it.each([false, true])("古い取得を無視する %s", async (failed) => {
  let finish!: (value: unknown) => void;
  vi.mocked(apiClient.get).mockImplementationOnce(() => new Promise((resolve, reject) => { finish = failed ? reject : resolve; })).mockResolvedValue("new");
  const { result, rerender } = renderHook(({ path }) => useResource(path), { initialProps: { path: "/old" } });
  rerender({ path: "/new" });
  await waitFor(() => expect(result.current.data).toBe("new"));
  await act(async () => finish(failed ? new Error() : "old"));
  expect(result.current.data).toBe("new");
});
it("二重操作を抑止", async () => {
  let finish!: () => void;
  vi.mocked(apiClient.get).mockResolvedValue({});
  vi.mocked(apiClient.post).mockImplementation(() => new Promise((resolve) => { finish = () => resolve({}); }));
  const { result } = renderHook(() => useResource("/items"));
  await waitFor(() => expect(result.current.data).toEqual({}));
  let first!: Promise<boolean>;
  act(() => { first = result.current.act("/items", {}); });
  await act(async () => expect(await result.current.act("/items", {})).toBe(false));
  await act(async () => { finish(); await first; });
  expect(apiClient.post).toHaveBeenCalledTimes(1);
});
it.each([false, true])("別対象へ移動後の保存応答を混ぜない %s", async (failed) => {
  let finish!: (value: unknown) => void;
  vi.mocked(apiClient.get).mockResolvedValue("item");
  vi.mocked(apiClient.post).mockImplementationOnce(() => new Promise((resolve, reject) => { finish = failed ? reject : resolve; }));
  const { result, rerender } = renderHook(({ path }) => useResource(path), { initialProps: { path: "/first" } });
  await waitFor(() => expect(result.current.data).toBe("item"));
  let pending!: Promise<boolean>;
  act(() => { pending = result.current.act("/save", {}); });
  rerender({ path: "/second" });
  await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith("/second"));
  await act(async () => { finish(failed ? new Error() : {}); await pending; });
  expect(apiClient.get).toHaveBeenCalledTimes(2);
  expect(result.current.error).toBeNull();
});
