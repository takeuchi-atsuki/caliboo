import { useEffect, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import type { AssignmentListItem, AssignmentListResponse } from "../../lib/types";

const NOTICE_AUTO_HIDE_MS = 5000;

export interface AssignmentListNotice {
  severity: "success" | "error";
  message: string;
}

export function useAssignmentList() {
  const [assignments, setAssignments] = useState<AssignmentListItem[]>([]);
  const [notice, setNotice] = useState<AssignmentListNotice | null>(null);
  const [creating, setCreating] = useState(false);

  const fetchAssignments = async () => {
    const data = await apiClient.get<AssignmentListResponse>("/api/assignments");
    setAssignments(data.assignments);
  };

  useEffect(() => {
    fetchAssignments();
  }, []);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), NOTICE_AUTO_HIDE_MS);
    return () => clearTimeout(timer);
  }, [notice]);

  const createAssignment = async (title: string, body: string) => {
    setCreating(true);
    try {
      await apiClient.post("/api/assignments", { title, body });
      await fetchAssignments();
      setNotice({ severity: "success", message: "課題を作成しました。" });
      return true;
    } catch {
      setNotice({
        severity: "error",
        message: "課題の作成に失敗しました。時間をおいて再度お試しください。",
      });
      return false;
    } finally {
      setCreating(false);
    }
  };

  return {
    assignments,
    notice,
    setNotice,
    creating,
    createAssignment,
  };
}
