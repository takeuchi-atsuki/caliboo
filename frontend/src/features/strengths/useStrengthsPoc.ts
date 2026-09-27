import { useEffect, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import type {
  PocPersonaListResponse,
  PocPersonaOption,
  PocRunDetail,
  PocRunListResponse,
  PocRunSummary,
} from "../../lib/types";

const NOTICE_AUTO_HIDE_MS = 5000;

export interface StrengthsNotice {
  severity: "success" | "error";
  message: string;
}

export function useStrengthsPoc() {
  const [personas, setPersonas] = useState<PocPersonaOption[]>([]);
  const [selectedPersonaKey, setSelectedPersonaKey] = useState("");
  const [runs, setRuns] = useState<PocRunSummary[]>([]);
  const [detail, setDetail] = useState<PocRunDetail | null>(null);
  const [running, setRunning] = useState(false);
  const [notice, setNotice] = useState<StrengthsNotice | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [personaData, runData] = await Promise.all([
          apiClient.get<PocPersonaListResponse>("/api/poc/personas"),
          apiClient.get<PocRunListResponse>("/api/poc/runs"),
        ]);
        setPersonas(personaData.personas);
        setSelectedPersonaKey(personaData.personas[0]?.personaKey ?? "");
        setRuns(runData.runs);
        if (runData.runs.length > 0) {
          setDetail(await apiClient.get<PocRunDetail>(`/api/poc/runs/${runData.runs[0].id}`));
        }
      } catch {
        setNotice({ severity: "error", message: "データの取得に失敗しました。" });
      }
    };
    load();
  }, []);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), NOTICE_AUTO_HIDE_MS);
    return () => clearTimeout(timer);
  }, [notice]);

  const startRun = async () => {
    if (!selectedPersonaKey) return;
    setRunning(true);
    try {
      const created = await apiClient.post<PocRunDetail>("/api/poc/runs", {
        personaKey: selectedPersonaKey,
      });
      setDetail(created);
      const runData = await apiClient.get<PocRunListResponse>("/api/poc/runs");
      setRuns(runData.runs);
      setNotice({ severity: "success", message: `解析が完了しました。（${created.id}）` });
    } catch {
      setNotice({
        severity: "error",
        message: "解析の実行に失敗しました。時間をおいて再度お試しください。",
      });
    } finally {
      setRunning(false);
    }
  };

  const selectRun = async (runId: string) => {
    try {
      setDetail(await apiClient.get<PocRunDetail>(`/api/poc/runs/${runId}`));
    } catch {
      setNotice({ severity: "error", message: "解析結果の取得に失敗しました。" });
    }
  };

  return {
    personas,
    selectedPersonaKey,
    setSelectedPersonaKey,
    runs,
    detail,
    running,
    notice,
    setNotice,
    startRun,
    selectRun,
  };
}
