import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient, ApiError } from "../../lib/apiClient";
import type { OjtConfiguration } from "../../lib/types";

const emptyConfiguration = (): OjtConfiguration => ({
  id: "", name: "", icon: "ph ph-code", color: "#d6ebff", welcomeMessage: "",
  quickAsks: [], replyGuidance: "", knowledge: [], revision: 0,
});

export function useOjtConfiguration(departmentId: string) {
  const [draft, setDraft] = useState<OjtConfiguration | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const version = useRef(0);
  const inFlight = useRef(false);

  const reload = useCallback(async () => {
    const current = ++version.current;
    setError(null); setSaved(false); setDraft(null);
    if (!departmentId) { setDraft(emptyConfiguration()); setLoading(false); return; }
    setLoading(true);
    try {
      const value = await apiClient.get<OjtConfiguration>(`/api/ojt/departments/${departmentId}/configuration`);
      if (current === version.current) setDraft(value);
    } catch {
      if (current === version.current) setError("設定を取得できませんでした。再読み込みしてください。");
    } finally {
      if (current === version.current) setLoading(false);
    }
  }, [departmentId]);

  useEffect(() => {
    void reload();
    return () => { version.current++; };
  }, [reload]);

  const save = async (): Promise<OjtConfiguration | null> => {
    if (!draft || loading || inFlight.current) return null;
    const current = version.current;
    inFlight.current = true; setSaving(true); setError(null); setSaved(false);
    const { id, revision, ...settings } = draft;
    try {
      const value = await apiClient.post<OjtConfiguration>(
        departmentId ? `/api/ojt/departments/${departmentId}/configuration` : "/api/ojt/departments",
        departmentId ? { ...settings, revision } : { ...settings, id },
      );
      if (current !== version.current) return null;
      setDraft(value); setSaved(true);
      return value;
    } catch (reason) {
      if (current === version.current) {
        setError(reason instanceof ApiError && reason.status === 409
          ? departmentId ? "他の講師が設定を更新しました。入力を控えてから最新の設定を読み直してください。" : "この部署IDは使用されています。別のIDを指定してください。"
          : "保存できませんでした。入力内容と接続を確認して再送してください。");
      }
      return null;
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  };

  return { draft, setDraft, loading, saving, error, saved, reload, save };
}
