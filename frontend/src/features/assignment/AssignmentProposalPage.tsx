import { useEffect, useState } from "react";
import { Link as RouterLink, Navigate, useNavigate, useParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";

import { PageContainer } from "../../components/layout/PageContainer";
import { Tag } from "../../components/badge/Tag";
import { PhosphorIcon } from "../../components/icon/PhosphorIcon";
import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { useAuth } from "../../components/auth/AuthProvider";
import { MOOD_OPTIONS } from "../../lib/moodOptions";
import {
  proposalMaterialKindLabel,
  proposalMaterialKindTone,
  proposalStatusLabel,
  proposalStatusTone,
} from "../../lib/proposalStatus";
import type { AssignmentDetail, ProposalDetail } from "../../lib/types";
import {
  APPROVE_SUCCESS_MESSAGE,
  REJECT_SUCCESS_MESSAGE,
  useAssignmentProposalDetail,
} from "./useAssignmentProposalDetail";

const panelStyle = { background: "var(--color-panel)", borderRadius: 20, padding: "20px 22px" };

export function AssignmentProposalPage() {
  const { proposalId } = useParams<{ proposalId: string }>();
  const parsedId = Number(proposalId);
  const { user } = useAuth();

  const { proposal, deliveredAssignment, notFound, notice, setNotice, submitting, approve, reject } =
    useAssignmentProposalDetail(parsedId);

  // !NOTE: 講師以外は(APIの応答を待たず)即座に一覧へ戻し、課題案画面を描画しない。
  //        `notFound`(講師以外の403・存在しないIDの404を区別しない)は、まだロールが
  //        確定していない一瞬や不正なIDへのフォールバックとして残す。
  if ((user && user.role !== "admin") || notFound) {
    return <Navigate to="/assignments" replace />;
  }

  return (
    <PageContainer>
      <div style={{ padding: "26px 30px", display: "flex", flexDirection: "column", gap: 20 }}>
        <Box
          component={RouterLink}
          to="/assignments?tab=proposals"
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
          AIの課題案に戻る
        </Box>

        {notice ? (
          <Alert severity={notice.severity} onClose={() => setNotice(null)}>
            {notice.message}
          </Alert>
        ) : null}

        {proposal ? (
          <>
            <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" }}>
              <span style={{ fontWeight: 800, fontSize: 20, color: "var(--color-text)" }}>課題案の確認</span>
              <Box component="span" sx={{ fontWeight: 700, fontSize: 13, color: "var(--color-text)" }}>
                {proposal.target.displayName}
              </Box>
              <Tag label={proposalStatusLabel(proposal.status)} tone={proposalStatusTone(proposal.status)} />
            </Box>

            {proposal.status === "approved" ? (
              <Box
                sx={{
                  borderRadius: "16px",
                  padding: "12px 16px",
                  background: "var(--color-green-100)",
                  color: "var(--color-green-500)",
                  fontWeight: 700,
                  fontSize: 13,
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  flexWrap: "wrap",
                }}
              >
                <PhosphorIcon name="ph-bold ph-check" size={16} />
                <span>
                  {proposal.decidedAt ? proposal.decidedAt.slice(0, 10) : ""} に
                  {proposal.decidedBy ? proposal.decidedBy.displayName : ""}
                  が配信しました{proposal.edited ? "（講師による修正あり）" : ""}
                </span>
                {proposal.assignmentId ? (
                  <Box
                    component={RouterLink}
                    to={`/assignments/${proposal.assignmentId}`}
                    sx={{ color: "var(--color-green-500)", fontWeight: 700, textDecoration: "underline" }}
                  >
                    配信した課題を見る
                  </Box>
                ) : null}
              </Box>
            ) : null}

            {proposal.status === "rejected" ? (
              <Box
                sx={{
                  borderRadius: "16px",
                  padding: "12px 16px",
                  background: "var(--color-bg-alt)",
                  color: "var(--color-text-sub2)",
                  fontWeight: 700,
                  fontSize: 13,
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                }}
              >
                <PhosphorIcon name="ph-bold ph-x" size={16} />
                <span>
                  {proposal.decidedAt ? proposal.decidedAt.slice(0, 10) : ""} に
                  {proposal.decidedBy ? proposal.decidedBy.displayName : ""}
                  が見送りました。理由: {proposal.rejectReason || "（記入なし）"}
                </span>
              </Box>
            ) : null}

            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", md: "1.2fr 1fr" },
                gap: "20px",
                alignItems: "flex-start",
              }}
            >
              <ProposalReviewForm
                proposal={proposal}
                deliveredAssignment={deliveredAssignment}
                submitting={submitting}
                onApprove={approve}
                onReject={reject}
              />
              <ProposalAnalysisPanel proposal={proposal} />
            </Box>
          </>
        ) : null}
      </div>
    </PageContainer>
  );
}

interface ProposalReviewFormProps {
  proposal: ProposalDetail;
  // 配信済み(approved)のとき、実際に配信された課題(assignments)の内容。課題案自体は
  // 生成時点の内容のまま変えない設計のため、配信後の表示はこちらを優先する(I2)。
  deliveredAssignment: AssignmentDetail | null;
  submitting: boolean;
  onApprove: (title: string, body: string, messageForMember: string) => Promise<boolean>;
  onReject: (reason: string) => Promise<boolean>;
}

/**
 * !NOTE: 配信する内容(タイトル・課題文・「この課題について・講師より」)の編集状態は、
 *        課題案の内容(props)から初期化してこのコンポーネントだけで持つ
 *        (`AssignmentSubmissionForm`と同じ構成)。ページ本体側にuseStateを置かないことで、
 *        `notFound`によるリダイレクトのような早期returnとフック呼び出し順の競合を避けている。
 */
function ProposalReviewForm({ proposal, deliveredAssignment, submitting, onApprove, onReject }: ProposalReviewFormProps) {
  const navigate = useNavigate();
  const editable = proposal.status === "pending";

  const [title, setTitle] = useState(proposal.title);
  const [body, setBody] = useState(proposal.body);
  const initialMessage = proposal.messageForMember ?? "";
  const [messageForMember, setMessageForMember] = useState(initialMessage);
  const [rejectReason, setRejectReason] = useState("");
  const [confirmAction, setConfirmAction] = useState<"approve" | "reject" | null>(null);

  useEffect(() => {
    setTitle(proposal.title);
    setBody(proposal.body);
    setMessageForMember(initialMessage);
  }, [proposal.id, proposal.title, proposal.body, initialMessage]);

  const edited = title !== proposal.title || body !== proposal.body || messageForMember !== initialMessage;
  const canApprove = editable && title.trim() !== "" && body.trim() !== "" && !submitting;

  // 配信済みは、課題案テーブル(生成時点のまま)ではなく実際に配信された課題の内容を表示する。
  // 見送りは配信された課題自体が無いため、課題案の内容(生成時点のまま)を表示する。
  const readOnlyTitle = proposal.status === "approved" ? deliveredAssignment?.title ?? proposal.title : proposal.title;
  const readOnlyBody = proposal.status === "approved" ? deliveredAssignment?.body ?? proposal.body : proposal.body;
  const readOnlyMessage =
    proposal.status === "approved" ? deliveredAssignment?.messageForMember ?? "" : proposal.messageForMember ?? "";

  const handleApprove = async () => {
    const ok = await onApprove(title, body, messageForMember);
    setConfirmAction(null);
    if (ok) {
      navigate("/assignments?tab=proposals", {
        state: { notice: { severity: "success", message: APPROVE_SUCCESS_MESSAGE } },
      });
    }
  };

  const handleReject = async () => {
    const ok = await onReject(rejectReason);
    setConfirmAction(null);
    if (ok) {
      navigate("/assignments?tab=proposals", {
        state: { notice: { severity: "success", message: REJECT_SUCCESS_MESSAGE } },
      });
    }
  };

  return (
    <div style={{ ...panelStyle, display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)" }}>
        {proposal.target.displayName}さんに配信する課題
      </div>

      <div>
        <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text-sub)", marginBottom: 6 }}>
          タイトル
        </div>
        {editable ? (
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            style={{
              width: "100%",
              boxSizing: "border-box",
              border: "1.5px solid var(--color-border)",
              background: "var(--color-bg)",
              borderRadius: 13,
              padding: "10px 13px",
              font: "500 13px/1.6 'M PLUS Rounded 1c'",
              color: "var(--color-text)",
            }}
          />
        ) : (
          <div style={{ fontWeight: 700, fontSize: 14, color: "var(--color-text)" }}>{readOnlyTitle}</div>
        )}
      </div>

      <div>
        <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text-sub)", marginBottom: 6 }}>
          課題文
        </div>
        {editable ? (
          <Textarea value={body} onChange={(event) => setBody(event.target.value)} />
        ) : (
          <div style={{ whiteSpace: "pre-wrap", fontSize: 13.5, color: "var(--color-text-sub2)" }}>
            {readOnlyBody}
          </div>
        )}
      </div>

      <div>
        <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text-sub)", marginBottom: 6 }}>
          この課題について・講師より
        </div>
        {editable ? (
          <Textarea value={messageForMember} onChange={(event) => setMessageForMember(event.target.value)} />
        ) : (
          <div style={{ whiteSpace: "pre-wrap", fontSize: 13.5, color: "var(--color-text-sub2)" }}>
            {readOnlyMessage || "（記入なし）"}
          </div>
        )}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontWeight: 700,
          fontSize: 12.5,
          color: "var(--color-text-sub2)",
        }}
      >
        <PhosphorIcon name="ph-bold ph-clock" size={13} />
        想定時間 {proposal.estimateMinutes}分
      </div>

      {editable ? (
        <>
          <div>
            <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text-sub)", marginBottom: 6 }}>
              見送る理由(任意)
            </div>
            <Textarea
              value={rejectReason}
              onChange={(event) => setRejectReason(event.target.value)}
              placeholder="例: 来週面談があるので今週は課題を増やさない"
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, flexWrap: "wrap" }}>
            <Button variant="secondary" disabled={submitting} onClick={() => setConfirmAction("reject")}>
              見送る
            </Button>
            <Button disabled={!canApprove} onClick={() => setConfirmAction("approve")}>
              {edited ? "修正して配信する" : "この内容で配信する"}
            </Button>
          </div>
        </>
      ) : null}

      <ConfirmDialog
        open={confirmAction === "approve"}
        title="課題の配信"
        message={`${proposal.target.displayName}さんの課題一覧に配信します。配信後はこの課題案を編集できません。`}
        confirmLabel="配信する"
        confirmColor="success"
        confirmDisabled={submitting}
        onConfirm={handleApprove}
        onCancel={() => setConfirmAction(null)}
      />
      <ConfirmDialog
        open={confirmAction === "reject"}
        title="課題案の見送り"
        message="この課題案を見送ります。よろしいですか？"
        confirmLabel="見送る"
        confirmDisabled={submitting}
        onConfirm={handleReject}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  );
}

function ProposalAnalysisPanel({ proposal }: { proposal: ProposalDetail }) {
  return (
    <div style={{ ...panelStyle, display: "flex", flexDirection: "column", gap: 14 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontWeight: 800,
          fontSize: 15,
          color: "var(--color-purple-500)",
        }}
      >
        <PhosphorIcon name="ph-bold ph-sparkle" size={16} />
        AIの分析
      </div>

      <div style={{ background: "var(--color-purple-100)", borderRadius: 16, padding: "14px 16px" }}>
        <div style={{ fontSize: 11.5, fontWeight: 700, color: "var(--color-purple-500)", letterSpacing: 0.4 }}>
          この課題のねらい
        </div>
        <div style={{ fontWeight: 800, fontSize: 15.5, marginTop: 2 }}>{proposal.aim}</div>
      </div>

      <div>
        <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text-sub)", marginBottom: 6 }}>
          提案した理由
        </div>
        <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-sub2)" }}>{proposal.rationale}</p>
      </div>

      <div>
        <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text-sub)", marginBottom: 8 }}>
          {proposal.target.displayName}さんの状況
        </div>
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "10px" }}>
          <Box sx={{ border: "1px solid var(--color-border)", borderRadius: "14px", padding: "10px 12px" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-sub)" }}>提出</div>
            <div style={{ fontSize: 20 }}>{proposal.progress.submittedCount}</div>
          </Box>
          <Box sx={{ border: "1px solid var(--color-border)", borderRadius: "14px", padding: "10px 12px" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-sub)" }}>フィードバック済み</div>
            <div style={{ fontSize: 20 }}>{proposal.progress.reviewedCount}</div>
          </Box>
          <Box sx={{ border: "1px solid var(--color-border)", borderRadius: "14px", padding: "10px 12px" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-sub)" }}>未提出</div>
            <div style={{ fontSize: 20 }}>{proposal.progress.notSubmittedCount}</div>
          </Box>
        </Box>
        <Box sx={{ display: "flex", gap: "4px", flexWrap: "wrap", alignItems: "center", marginTop: "10px" }}>
          <Box component="span" sx={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-sub)", marginRight: "4px" }}>
            直近のきもち
          </Box>
          {proposal.progress.recentMoods.length > 0 ? (
            proposal.progress.recentMoods.map((mood, index) => {
              const option = MOOD_OPTIONS.find((item) => item.value === mood);
              return (
                <Box
                  key={index}
                  component="span"
                  sx={{
                    fontSize: 10.5,
                    fontWeight: 700,
                    color: option?.fg ?? "var(--color-text-sub)",
                    background: option?.bg ?? "var(--color-bg-alt)",
                    borderRadius: "8px",
                    padding: "2px 7px",
                  }}
                >
                  {option?.label ?? mood}
                </Box>
              );
            })
          ) : (
            <Box component="span" sx={{ fontSize: 12, color: "var(--color-text-sub)" }}>
              日報の記録なし
            </Box>
          )}
        </Box>
      </div>

      <div>
        <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text-sub)", marginBottom: 6 }}>
          分析した材料 {proposal.materials.length}件
        </div>
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column" }}>
          {proposal.materials.map((material, index) => (
            <li
              key={index}
              style={{
                display: "grid",
                gridTemplateColumns: "96px minmax(0, 1fr)",
                gap: 12,
                padding: "11px 0",
                borderTop: index === 0 ? "none" : "1px solid var(--color-bg)",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 3, alignItems: "flex-start" }}>
                <Tag label={proposalMaterialKindLabel(material.kind)} tone={proposalMaterialKindTone(material.kind)} />
                {material.date ? (
                  <span style={{ fontSize: 11, color: "var(--color-text-sub)" }}>{material.date}</span>
                ) : null}
              </div>
              <div>
                <span style={{ fontSize: 13 }}>「{material.quote}」</span>
                {material.sourceLabel !== proposalMaterialKindLabel(material.kind) ? (
                  <span style={{ display: "block", fontSize: 11.5, color: "var(--color-text-sub)", marginTop: 2 }}>
                    {material.sourceLabel}
                  </span>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
