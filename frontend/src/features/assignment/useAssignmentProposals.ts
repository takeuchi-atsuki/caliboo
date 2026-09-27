import { useEffect, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import type {
  ProposalDetail,
  ProposalListItem,
  ProposalListResponse,
  ProposalMember,
  ProposalStatus,
} from "../../lib/types";

const NOTICE_AUTO_HIDE_MS = 5000;

export interface AssignmentProposalsNotice {
  severity: "success" | "error";
  message: string;
}

/**
 * !NOTE: 課題案API(`/api/assignment-proposals`)は講師専用(新入社員は403)のため、
 *        呼び出し元(`AssignmentListPage`)がロールに応じて`enabled`をfalseにすることで、
 *        新入社員での不要なAPI呼び出し・エラー通知を避ける。
 */
export function useAssignmentProposals(status: ProposalStatus, enabled: boolean) {
  const [proposals, setProposals] = useState<ProposalListItem[]>([]);
  const [members, setMembers] = useState<ProposalMember[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [notice, setNotice] = useState<AssignmentProposalsNotice | null>(null);
  const [generating, setGenerating] = useState(false);

  const fetchProposals = async () => {
    try {
      const data = await apiClient.get<ProposalListResponse>(`/api/assignment-proposals?status=${status}`);
      setProposals(data.proposals);
      setMembers(data.members);
      setPendingCount(data.pendingCount);
    } catch {
      // !NOTE: マウント時・status切替時の取得失敗をここで拾わないと、未処理のPromise拒否になる
      //        (`useAssignmentDetail`のfetchAssignmentと同じ理由)。
      setNotice({
        severity: "error",
        message: "課題案の取得に失敗しました。時間をおいて再度お試しください。",
      });
    }
  };

  useEffect(() => {
    if (!enabled) return;
    fetchProposals();
  }, [status, enabled]);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), NOTICE_AUTO_HIDE_MS);
    return () => clearTimeout(timer);
  }, [notice]);

  const generateProposal = async (userId: number): Promise<ProposalDetail | null> => {
    setGenerating(true);
    try {
      const created = await apiClient.post<ProposalDetail>("/api/assignment-proposals", { userId });
      await fetchProposals();
      return created;
    } catch {
      setNotice({
        severity: "error",
        message: "課題案の作成に失敗しました。時間をおいて再度お試しください。",
      });
      return null;
    } finally {
      setGenerating(false);
    }
  };

  return {
    proposals,
    members,
    pendingCount,
    notice,
    setNotice,
    generating,
    generateProposal,
  };
}
