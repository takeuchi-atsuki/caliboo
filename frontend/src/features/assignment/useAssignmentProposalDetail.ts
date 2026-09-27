import { useEffect, useState } from "react";

import { ApiError, apiClient } from "../../lib/apiClient";
import type { AssignmentDetail, ProposalDetail } from "../../lib/types";

const NOTICE_AUTO_HIDE_MS = 5000;

export interface AssignmentProposalDetailNotice {
  severity: "success" | "error";
  message: string;
}

// 一覧画面(`AssignmentListPage`)へ成功通知を引き継ぐ(navigateのstate経由)ために公開する。
export const APPROVE_SUCCESS_MESSAGE = "課題を配信しました。";
export const REJECT_SUCCESS_MESSAGE = "課題案を見送りました。";

const CONFLICT_RELOAD_SUFFIX = "最新の状態を再読み込みします。";

/**
 * !NOTE: 取得失敗はロール(講師以外は403)・存在しないID(404)のいずれも区別せず
 *        notFoundとして扱う。`useAssignmentDetail`と同じ考え方で、呼び出し側
 *        (`AssignmentProposalPage`)は理由によらず一覧へ戻すだけでよい。
 */
export function useAssignmentProposalDetail(proposalId: number) {
  const [proposal, setProposal] = useState<ProposalDetail | null>(null);
  const [deliveredAssignment, setDeliveredAssignment] = useState<AssignmentDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [notice, setNotice] = useState<AssignmentProposalDetailNotice | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchProposal = async () => {
    try {
      const data = await apiClient.get<ProposalDetail>(`/api/assignment-proposals/${proposalId}`);
      setProposal(data);
    } catch {
      setNotFound(true);
    }
  };

  useEffect(() => {
    fetchProposal();
  }, [proposalId]);

  // !NOTE: 配信済みの課題案は、課題案テーブル自体(生成時点の内容のまま変えない設計)ではなく
  //        「実際に配信された課題(assignments)」の内容を表示する。承認時に講師が編集していると
  //        (`edited`)、課題案のtitle/body/messageForMemberは生成時点のままで実際の配信内容と
  //        食い違うため。
  useEffect(() => {
    if (!proposal || proposal.status !== "approved" || !proposal.assignmentId) {
      setDeliveredAssignment(null);
      return;
    }
    let cancelled = false;
    apiClient
      .get<AssignmentDetail>(`/api/assignments/${proposal.assignmentId}`)
      .then((data) => {
        if (!cancelled) setDeliveredAssignment(data);
      })
      .catch(() => {
        if (!cancelled) setDeliveredAssignment(null);
      });
    return () => {
      cancelled = true;
    };
  }, [proposal?.status, proposal?.assignmentId]);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(null), NOTICE_AUTO_HIDE_MS);
    return () => clearTimeout(timer);
  }, [notice]);

  const approve = async (title: string, body: string, messageForMember: string): Promise<boolean> => {
    setSubmitting(true);
    try {
      const data = await apiClient.post<ProposalDetail>(`/api/assignment-proposals/${proposalId}/approve`, {
        title,
        body,
        messageForMember,
      });
      setProposal(data);
      setNotice({ severity: "success", message: APPROVE_SUCCESS_MESSAGE });
      return true;
    } catch (error) {
      // !NOTE: 409(確認待ち以外への操作)は、別タブ等で既に決定済みになっている状態を
      //        示すため、表示中の課題案を再取得して最新の状態に合わせる
      //        (`useAssignmentDetail`のsubmitAnswer失敗時と同じ考え方)。
      if (error instanceof ApiError && error.status === 409) {
        setNotice({
          severity: "error",
          message: `既に決定済みのため配信できませんでした。${CONFLICT_RELOAD_SUFFIX}`,
        });
        await fetchProposal();
      } else {
        setNotice({
          severity: "error",
          message: "配信できませんでした。時間をおいて再度お試しください。",
        });
      }
      return false;
    } finally {
      setSubmitting(false);
    }
  };

  const reject = async (reason: string): Promise<boolean> => {
    setSubmitting(true);
    try {
      const data = await apiClient.post<ProposalDetail>(`/api/assignment-proposals/${proposalId}/reject`, {
        reason: reason.trim() === "" ? null : reason,
      });
      setProposal(data);
      setNotice({ severity: "success", message: REJECT_SUCCESS_MESSAGE });
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setNotice({
          severity: "error",
          message: `既に決定済みのため見送れませんでした。${CONFLICT_RELOAD_SUFFIX}`,
        });
        await fetchProposal();
      } else {
        setNotice({
          severity: "error",
          message: "見送りできませんでした。時間をおいて再度お試しください。",
        });
      }
      return false;
    } finally {
      setSubmitting(false);
    }
  };

  return {
    proposal,
    deliveredAssignment,
    notFound,
    notice,
    setNotice,
    submitting,
    approve,
    reject,
  };
}
