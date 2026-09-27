import { useState, useEffect } from "react";

import { apiClient } from "../../lib/apiClient";
import type {
  Mood,
  ReportDraftItem,
  ReportDraftListResponse,
  ReportHistoryItem,
  ReportHistoryResponse,
  ReportRequest,
  ReportResponse,
  ReportStatus,
} from "../../lib/types";
import { clearAutosave, readAutosave, writeAutosave, type ReportAutosave } from "./reportAutosave";

const today = () => new Date().toISOString().slice(0, 10);

const FEEDBACK_AUTO_HIDE_MS = 5000;

export interface ReportFormFeedback {
  severity: "success" | "error";
  message: string;
}

export function useReportForm(userId: number) {
  const [keep, setKeep] = useState("");
  const [problem, setProblem] = useState("");
  const [tryText, setTryText] = useState("");
  const [mood, setMood] = useState<Mood[]>([]);
  const [moodComment, setMoodComment] = useState("");
  const [feedback, setFeedback] = useState<ReportFormFeedback | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [history, setHistory] = useState<ReportHistoryItem[]>([]);
  const [drafts, setDrafts] = useState<ReportDraftItem[]>([]);
  const [draftDate, setDraftDate] = useState<string | null>(null);
  const [pendingRestore, setPendingRestore] = useState<ReportAutosave | null>(() =>
    readAutosave(userId),
  );
  // ユーザーが編集を始めてから自動保存する。初期表示の空フォームで前回の入力内容を上書きしないため
  const [autosaveEnabled, setAutosaveEnabled] = useState(false);

  const fetchHistory = async () => {
    const data = await apiClient.get<ReportHistoryResponse>("/api/report/history");
    setHistory(data.history);
  };

  const fetchDrafts = async () => {
    const data = await apiClient.get<ReportDraftListResponse>("/api/report/drafts");
    setDrafts(data.drafts);
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    if (!autosaveEnabled || pendingRestore) return;
    writeAutosave({ keep, problem, try: tryText, mood, moodComment, draftDate }, userId);
  }, [autosaveEnabled, pendingRestore, keep, problem, tryText, mood, moodComment, draftDate, userId]);

  useEffect(() => {
    if (!feedback) return;
    const timer = setTimeout(() => setFeedback(null), FEEDBACK_AUTO_HIDE_MS);
    return () => clearTimeout(timer);
  }, [feedback]);

  const withAutosave =
    <T,>(setter: (value: T) => void) =>
    (value: T) => {
      setter(value);
      setAutosaveEnabled(true);
    };

  // 提出や「新規作成に戻す」で編集が完了した入力内容は、再読み込み時に復元候補として出さない。
  // ただし復元確認中は、利用者が選ぶ前の再読み込みで前回の入力を失わないよう消去しない(docs/screens/report.md参照)
  const finishEditing = () => {
    setAutosaveEnabled(false);
    if (!pendingRestore) clearAutosave();
  };

  const restoreAutosave = () => {
    if (!pendingRestore) return;
    setKeep(pendingRestore.keep);
    setProblem(pendingRestore.problem);
    setTryText(pendingRestore.try);
    setMood(pendingRestore.mood);
    setMoodComment(pendingRestore.moodComment);
    setDraftDate(pendingRestore.draftDate);
    setFeedback(null);
    setPendingRestore(null);
    setAutosaveEnabled(true);
  };

  const discardAutosave = () => {
    clearAutosave();
    setPendingRestore(null);
  };

  const loadDraft = (item: ReportDraftItem) => {
    setKeep(item.keep);
    setProblem(item.problem);
    setTryText(item.try);
    setMood(item.mood);
    setMoodComment(item.moodComment);
    setDraftDate(item.date);
    setFeedback(null);
    setAutosaveEnabled(true);
  };

  const clearDraft = () => {
    setKeep("");
    setProblem("");
    setTryText("");
    setMood([]);
    setMoodComment("");
    setDraftDate(null);
    setFeedback(null);
    finishEditing();
  };

  const deleteDraft = async (id: number) => {
    try {
      await apiClient.del(`/api/report/drafts/${id}`);
      setDrafts((prev) => prev.filter((draft) => draft.id !== id));
    } catch {
      setFeedback({ severity: "error", message: "下書きの削除に失敗しました。時間をおいて再度お試しください。" });
    }
  };

  const submit = async (status: ReportStatus) => {
    setSubmitting(true);
    try {
      const payload: ReportRequest = {
        date: draftDate ?? today(),
        keep,
        problem,
        try: tryText,
        mood,
        moodComment,
        status,
      };
      const result = await apiClient.post<ReportResponse>("/api/report", payload);
      setFeedback({
        severity: "success",
        message: status === "submitted" ? `提出しました！（${result.id}）` : "下書きを保存しました。",
      });
      if (status === "submitted") {
        await fetchHistory();
        setDraftDate(null);
        finishEditing();
      } else {
        await fetchDrafts();
      }
      return result;
    } catch {
      setFeedback({
        severity: "error",
        message:
          status === "submitted"
            ? "提出に失敗しました。時間をおいて再度お試しください。"
            : "下書きの保存に失敗しました。時間をおいて再度お試しください。",
      });
      return null;
    } finally {
      setSubmitting(false);
    }
  };

  return {
    keep,
    setKeep: withAutosave(setKeep),
    problem,
    setProblem: withAutosave(setProblem),
    tryText,
    setTryText: withAutosave(setTryText),
    mood,
    setMood: withAutosave(setMood),
    moodComment,
    setMoodComment: withAutosave(setMoodComment),
    feedback,
    setFeedback,
    submitting,
    submit,
    history,
    drafts,
    draftDate,
    fetchDrafts,
    loadDraft,
    clearDraft,
    deleteDraft,
    pendingRestore,
    restoreAutosave,
    discardAutosave,
  };
}
