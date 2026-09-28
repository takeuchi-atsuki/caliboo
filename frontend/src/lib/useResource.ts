import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "./apiClient";
import { useAutoRefresh } from "./useAutoRefresh";

/** パス変更・アンマウント後の古い応答を破棄する共通の取得処理。 */
export function useResource<T>(path: string | null, refreshMs = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const version = useRef(0);
  const currentPath = useRef(path);
  currentPath.current = path;
  const acting = useRef(false);
  const fetching = useRef<{ path: string; version: number } | null>(null);
  const reload = useCallback(async (background = false) => {
    if (background && (fetching.current?.path === path || acting.current)) return;
    const current = ++version.current;
    if (!path) { setData(null); return; }
    fetching.current = { path, version: current };
    try {
      const value = await apiClient.get<T>(path);
      if (current === version.current) { setData(value); setError(null); }
    } catch {
      if (current === version.current) setError("読み込みに失敗しました。再読み込みしてください。");
    } finally {
      if (fetching.current?.version === current) fetching.current = null;
    }
  }, [path]);
  const refresh = useCallback(() => reload(true), [reload]);
  useAutoRefresh(refresh, path ? refreshMs : 0);
  useEffect(() => {
    setData(null);
    void reload();
    return () => { version.current++; };
  }, [reload]);
  const act = async (target: string, body: unknown): Promise<boolean> => {
    if (acting.current) return false;
    acting.current = true;
    setBusy(true);
    setError(null);
    try {
      await apiClient.post(target, body);
      if (currentPath.current === path) await reload();
      return true;
    } catch {
      if (currentPath.current === path) setError("保存できませんでした。入力内容と最新の状態を確認してください。");
      return false;
    } finally {
      acting.current = false;
      setBusy(false);
    }
  };
  return { data, error, busy, reload, act };
}
