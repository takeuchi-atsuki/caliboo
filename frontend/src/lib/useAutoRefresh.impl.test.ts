import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useAutoRefresh } from "./useAutoRefresh";
beforeEach(() => { vi.useFakeTimers(); vi.spyOn(document, "hidden", "get").mockReturnValue(false); });
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });
it("5秒間隔、非表示で停止、復帰時取得、解除", async () => {
  const refresh = vi.fn().mockResolvedValue(undefined);
  const { unmount } = renderHook(() => useAutoRefresh(refresh, 5000));
  await act(async () => vi.advanceTimersByTimeAsync(4999)); expect(refresh).not.toHaveBeenCalled();
  await act(async () => vi.advanceTimersByTimeAsync(1)); expect(refresh).toHaveBeenCalledTimes(1);
  vi.spyOn(document, "hidden", "get").mockReturnValue(true);
  act(() => document.dispatchEvent(new Event("visibilitychange")));
  await act(async () => vi.advanceTimersByTimeAsync(20000)); expect(refresh).toHaveBeenCalledTimes(1);
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  await act(async () => document.dispatchEvent(new Event("visibilitychange"))); expect(refresh).toHaveBeenCalledTimes(2);
  unmount(); await act(async () => vi.advanceTimersByTimeAsync(20000)); expect(refresh).toHaveBeenCalledTimes(2);
});
it("遅い通信を重ねず、解除後はタイマーを再開しない", async () => {
  let finish!: () => void;
  const refresh = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
  const { unmount } = renderHook(() => useAutoRefresh(refresh, 5000));
  await act(async () => vi.advanceTimersByTimeAsync(5000));
  act(() => document.dispatchEvent(new Event("visibilitychange")));
  await act(async () => vi.advanceTimersByTimeAsync(20000)); expect(refresh).toHaveBeenCalledTimes(1);
  unmount(); await act(async () => finish()); expect(vi.getTimerCount()).toBe(0);
});
it("無効時・非表示時は取得しない", async () => {
  const refresh = vi.fn().mockResolvedValue(undefined);
  const { rerender } = renderHook(({ interval }) => useAutoRefresh(refresh, interval), { initialProps: { interval: 0 } });
  expect(vi.getTimerCount()).toBe(0); rerender({ interval: 5000 });
  vi.spyOn(document, "hidden", "get").mockReturnValue(true);
  await act(async () => vi.advanceTimersByTimeAsync(5000)); expect(refresh).not.toHaveBeenCalled();
});
