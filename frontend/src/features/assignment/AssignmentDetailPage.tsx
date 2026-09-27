import { useEffect, useState } from "react";
import { Link as RouterLink, Navigate, useParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";

import { PageContainer } from "../../components/layout/PageContainer";
import { Tag } from "../../components/badge/Tag";
import { PhosphorIcon } from "../../components/icon/PhosphorIcon";
import { useAuth } from "../../components/auth/AuthProvider";
import { apiClient } from "../../lib/apiClient";
import { assignmentStatusLabel, assignmentStatusTone } from "../../lib/assignmentStatus";
import type { ProposalListItem, ProposalListResponse } from "../../lib/types";
import { useAssignmentDetail } from "./useAssignmentDetail";
import { AssignmentSubmissionForm, ReadOnlyAnswer } from "./AssignmentSubmissionForm";
import { AssignmentFeedbackForm } from "./AssignmentFeedbackForm";

const panelStyle = { background: "var(--color-panel)", borderRadius: 20, padding: "20px 22px" };

export function AssignmentDetailPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const parsedId = Number(assignmentId);
  const { user } = useAuth();
  // !NOTE: フック呼び出し順を安定させるため、`user`がまだ無い場合のフォールバック値
  //        (`user`は通常必ず存在する。下記の早期returnのNOTE参照)で全フックを
  //        先に宣言してから、描画の分岐(早期return)は最後にまとめて行う(I11)。
  const role = user?.role ?? "member";

  const { assignment, submissions, notFound, notice, setNotice, submitting, submitAnswer, submitFeedback } =
    useAssignmentDetail(parsedId, role);

  const [originProposal, setOriginProposal] = useState<ProposalListItem | null>(null);

  // !NOTE: 課題案からの導線(講師のみ)は、既存課題APIに`proposalId`を持たせず
  //        (設計レビュー反映: AI由来を新入社員側へ漏らさないため)、課題案API側の
  //        `assignmentId`フィルタから逆引きする。取得できなくても課題自体の閲覧は
  //        妨げないため、失敗時は単に「元の課題案へのリンクを出さない」だけにする。
  useEffect(() => {
    if (role !== "admin" || !assignment) {
      setOriginProposal(null);
      return;
    }
    let cancelled = false;
    apiClient
      .get<ProposalListResponse>(`/api/assignment-proposals?assignmentId=${assignment.id}`)
      .then((data) => {
        if (!cancelled) setOriginProposal(data.proposals[0] ?? null);
      })
      .catch(() => {
        if (!cancelled) setOriginProposal(null);
      });
    return () => {
      cancelled = true;
    };
  }, [role, assignment?.id]);

  // !NOTE: RequireAuthが未ログイン中はこのページ自体を描画しないため、通常は必ずuserが
  //        存在する。型を絞り込むためのガードで、実際に到達することは想定していない。
  if (!user) {
    return null;
  }

  if (notFound) {
    return <Navigate to="/assignments" replace />;
  }

  return (
    <PageContainer>
      <div style={{ padding: "26px 30px", display: "flex", flexDirection: "column", gap: 20 }}>
        <Box
          component={RouterLink}
          to="/assignments"
          sx={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            color: "var(--color-text-sub)",
            fontWeight: 700,
            fontSize: 12.5,
            textDecoration: "none",
            width: "fit-content",
          }}
        >
          <PhosphorIcon name="ph-bold ph-arrow-left" size={14} />
          課題一覧に戻る
        </Box>

        {notice ? (
          <Alert severity={notice.severity} onClose={() => setNotice(null)}>
            {notice.message}
          </Alert>
        ) : null}

        {assignment ? (
          <>
            <div style={panelStyle}>
              <Box sx={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px", flexWrap: "wrap" }}>
                <span style={{ fontWeight: 800, fontSize: 20, color: "var(--color-text)" }}>{assignment.title}</span>
                <Tag label={assignmentStatusLabel(assignment.status)} tone={assignmentStatusTone(assignment.status)} />
                {user.role === "admin" ? (
                  <Box component="span" sx={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text-sub)" }}>
                    配信先: {assignment.target ? assignment.target.displayName : "全員"}
                  </Box>
                ) : null}
                {user.role === "member" && assignment.target ? <Tag label="あなた向け" tone="purple" /> : null}
              </Box>

              {assignment.messageForMember ? (
                <Box
                  sx={{
                    borderRadius: "16px",
                    padding: "14px 16px",
                    background: "var(--color-green-100)",
                    marginBottom: "14px",
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      fontWeight: 800,
                      fontSize: 12,
                      color: "var(--color-green-500)",
                    }}
                  >
                    <PhosphorIcon name="ph-bold ph-chat-circle-text" size={14} />
                    この課題について・講師より
                  </Box>
                  <Box sx={{ fontSize: 13, color: "var(--color-text)", marginTop: "6px" }}>
                    {assignment.messageForMember}
                  </Box>
                </Box>
              ) : null}

              <div style={{ whiteSpace: "pre-wrap", fontSize: 13.5, color: "var(--color-text-sub2)" }}>
                {assignment.body}
              </div>

              {user.role === "admin" && originProposal ? (
                <Box
                  component={RouterLink}
                  to={`/assignments/proposals/${originProposal.id}`}
                  sx={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    marginTop: "14px",
                    color: "var(--color-text-sub2)",
                    fontWeight: 700,
                    fontSize: 12.5,
                    textDecoration: "none",
                    border: "1px solid var(--color-border)",
                    borderRadius: "11px",
                    padding: "7px 14px",
                  }}
                >
                  <PhosphorIcon name="ph-bold ph-sparkle" size={14} />
                  元の課題案とAIの分析を見る
                </Box>
              ) : null}
            </div>

            {user.role === "member" ? (
              <>
                <div style={panelStyle}>
                  <AssignmentSubmissionForm assignment={assignment} submitting={submitting} onSubmit={submitAnswer} />
                </div>

                {assignment.submission?.feedbackComment ? (
                  <div style={panelStyle}>
                    <div style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)", marginBottom: 10 }}>
                      講師からのフィードバック
                    </div>
                    <div style={{ whiteSpace: "pre-wrap", fontSize: 13.5, color: "var(--color-text-sub2)" }}>
                      {assignment.submission.feedbackComment}
                    </div>
                  </div>
                ) : null}
              </>
            ) : (
              <div style={panelStyle}>
                <div style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)", marginBottom: 14 }}>
                  新入社員ごとの提出
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                  {submissions.map((item) => (
                    <div
                      key={item.user.id}
                      style={{
                        borderTop: "1px solid var(--color-bg)",
                        paddingTop: 16,
                        display: "flex",
                        flexDirection: "column",
                        gap: 10,
                      }}
                    >
                      <Box sx={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span style={{ fontWeight: 800, fontSize: 14, color: "var(--color-text)" }}>
                          {item.user.displayName}
                        </span>
                        <Tag label={assignmentStatusLabel(item.status)} tone={assignmentStatusTone(item.status)} />
                      </Box>
                      {item.submission ? (
                        <ReadOnlyAnswer text={item.submission.answerText} />
                      ) : (
                        <div style={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>
                          まだ回答が提出されていません。
                        </div>
                      )}
                      <AssignmentFeedbackForm
                        assignmentId={parsedId}
                        status={item.status}
                        submission={item.submission}
                        submitting={submitting}
                        onSubmit={(comment) => submitFeedback(item.user.id, comment)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : null}
      </div>
    </PageContainer>
  );
}
