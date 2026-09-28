import { useEffect } from "react";

/** 表示中のみ取得し、前の定期取得が終わるまで次を開始しない。 */
export function useAutoRefresh(refresh: () => Promise<unknown>, intervalMs = 0) {
  useEffect(() => {
    if (!intervalMs) return;
    let active = true;
    let running = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const schedule = () => {
      clearTimeout(timer);
      if (active && !document.hidden) timer = setTimeout(() => void run(), intervalMs);
    };
    const run = async () => {
      if (!active || document.hidden || running) return;
      running = true;
      try { await refresh(); }
      finally { running = false; schedule(); }
    };
    const visibilityChanged = () => {
      clearTimeout(timer);
      if (!document.hidden) void run();
    };
    schedule();
    document.addEventListener("visibilitychange", visibilityChanged);
    return () => {
      active = false;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", visibilityChanged);
    };
  }, [refresh, intervalMs]);
}
