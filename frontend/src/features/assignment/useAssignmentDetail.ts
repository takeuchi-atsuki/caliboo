import { useEffect, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import type { UserRole } from "../../components/auth/AuthProvider";
import type { AssignmentDetail, MemberSubmission, MemberSubmissionListResponse } from "../../lib/types";

const NOTICE_AUTO_HIDE_MS = 5000;

export interface AssignmentDetailNotice {
  severity: "success" | "error";
  message: string;
}

/**
 * !NOTE: 提出一覧(`GET /api/assignments/{id}/submissions`)はadmin専用API(memberは403)
 *        のため、adminのときだけ取得する。memberの一覧・詳細APIの`status`/`submission`は
 *        常に本人の提出を表すため、member側のロジックはロール分岐なしで従来どおり動く。
 */
export function useAssignmentDetail(assignmentId: number, role: UserRole) {
  const [assignment, setAssignment] = useState<AssignmentDetail | null>(null);
  const [submissions, setSubmissions] = useState<MemberSubmission[]>([]);
  const [notFound, setNotFound] = useState(false);
  const [notice, setNotice] = useState<AssignmentDetailNotice | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchAssignment = async () => {
    try {
      const data = await apiClient.get<AssignmentDetail>(`/api/assignments/${assignmentId}`);
      setAssignment(data);
    } catch {
      setNotFound(true);
    }
  };

  // !NOTE: 存在しない課題IDの場合、詳細(fetchAssignment)と一覧の両方が404になりうる。
  //        詳細側は`notFound`を立てて一覧画面へリダイレクトするため、こちらは失敗を
  //        飲み込むだけにして未処理のPromise拒否を防ぐ(状態は空配列のまま)。
  const fetchSubmissions = async () => {
    try {
      const data = await apiClient.get<MemberSubmissionListResponse>(
        `/api/assignments/${assignmentId}/submissions`,
      );
      setSubmissions(data.submissions);
    } catch {
      // 404等はfetchAssignment側のnotFoundで処理されるため、ここでは何もしない
    }
  };

  useEffect(() => {
    fetchAssignment();
    if (role === "admin") {
      fetchSubmissions();
    }
  }, [assignmentId, role]);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), NOTICE_AUTO_HIDE_MS);
    return () => clearTimeout(timer);
  }, [notice]);

  const submitAnswer = async (answerText: string) => {
    setSubmitting(true);
    try {
      const data = await apiClient.post<AssignmentDetail>(
        `/api/assignments/${assignmentId}/submission`,
        { answerText }
      );
      setAssignment(data);
      setNotice({ severity: "success", message: "回答を提出しました。" });
    } catch {
      setNotice({
        severity: "error",
        message: "保存できませんでした。最新の状態を再読み込みします。",
      });
      await fetchAssignment();
    } finally {
      setSubmitting(false);
    }
  };

  const submitFeedback = async (userId: number, comment: string, score?: number | null) => {
    setSubmitting(true);
    try {
      const data = await apiClient.post<MemberSubmission>(
        `/api/assignments/${assignmentId}/submissions/${userId}/feedback`,
        { comment, ...(score !== undefined ? { score } : {}) }
      );
      setSubmissions((prev) => prev.map((item) => (item.user.id === userId ? data : item)));
      setNotice({ severity: "success", message: "フィードバックを保存しました。" });
    } catch {
      setNotice({
        severity: "error",
        message: "保存できませんでした。最新の状態を再読み込みします。",
      });
      await fetchSubmissions();
    } finally {
      setSubmitting(false);
    }
  };

  return {
    assignment,
    submissions,
    notFound,
    notice,
    setNotice,
    submitting,
    submitAnswer,
    submitFeedback,
  };
}
