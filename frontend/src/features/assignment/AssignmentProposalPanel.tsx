import { useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Table from "@mui/material/Table";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableBody from "@mui/material/TableBody";
import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";

import { Button } from "../../components/ui/Button";
import { Tag } from "../../components/badge/Tag";
import { PROPOSAL_STATUS_OPTIONS, proposalStatusLabel, proposalStatusTone } from "../../lib/proposalStatus";
import type { ProposalDetail, ProposalListItem, ProposalMember, ProposalStatus } from "../../lib/types";
import type { AssignmentProposalsNotice } from "./useAssignmentProposals";

export interface AssignmentProposalPanelProps {
  status: ProposalStatus;
  onStatusChange: (status: ProposalStatus) => void;
  proposals: ProposalListItem[];
  members: ProposalMember[];
  notice: AssignmentProposalsNotice | null;
  setNotice: (notice: AssignmentProposalsNotice | null) => void;
  generating: boolean;
  generateProposal: (userId: number) => Promise<ProposalDetail | null>;
}

const headerCellSx = {
  textAlign: "left" as const,
  fontSize: 11.5,
  color: "var(--color-text-sub)",
  fontWeight: 700,
  paddingBottom: "8px",
  borderBottom: "1.5px solid var(--color-bg)",
};

const bodyCellSx = {
  fontSize: 13,
  color: "var(--color-text)",
  padding: "10px 0",
  borderBottom: "1px solid var(--color-bg)",
};

/**
 * !NOTE: 課題案の一覧・生成・状態フィルタを担う「見た目主体」のコンポーネント。
 *        API呼び出しは`useAssignmentProposals`(親の`AssignmentListPage`)が担い、
 *        ここは受け取ったデータ・コールバックを描画するだけにしている。
 */
export function AssignmentProposalPanel({
  status,
  onStatusChange,
  proposals,
  members,
  notice,
  setNotice,
  generating,
  generateProposal,
}: AssignmentProposalPanelProps) {
  const navigate = useNavigate();
  const [selectedMemberId, setSelectedMemberId] = useState("");

  const handleGenerate = async () => {
    if (!selectedMemberId) return;
    const created = await generateProposal(Number(selectedMemberId));
    if (created) {
      navigate(`/assignments/proposals/${created.id}`);
    }
  };

  return (
    <div
      style={{
        background: "var(--color-panel)",
        borderRadius: 20,
        padding: "20px 22px",
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      {notice ? (
        <Alert severity={notice.severity} onClose={() => setNotice(null)}>
          {notice.message}
        </Alert>
      ) : null}

      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: "12px",
          alignItems: "flex-end",
          justifyContent: "space-between",
        }}
      >
        <Box sx={{ display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "flex-end" }}>
          <TextField
            select
            size="small"
            label="新入社員"
            value={selectedMemberId}
            onChange={(event) => setSelectedMemberId(event.target.value)}
            sx={{ minWidth: 200 }}
          >
            {members.map((member) => (
              <MenuItem key={member.id} value={String(member.id)}>
                {member.displayName}
                {member.hasPending ? "（確認待ちあり）" : ""}
              </MenuItem>
            ))}
          </TextField>
          <Button icon="ph-bold ph-sparkle" disabled={!selectedMemberId || generating} onClick={handleGenerate}>
            {generating ? "作成しています…" : "課題案をつくる"}
          </Button>
        </Box>

        <Box sx={{ display: "flex", gap: "6px", flexWrap: "wrap" }} role="group" aria-label="状態で絞り込む">
          {PROPOSAL_STATUS_OPTIONS.map((option) => (
            <Box
              key={option.value}
              component="button"
              type="button"
              onClick={() => onStatusChange(option.value)}
              aria-pressed={status === option.value}
              sx={{
                border: "1px solid var(--color-border)",
                background: status === option.value ? "var(--color-green-100)" : "var(--color-panel)",
                color: status === option.value ? "var(--color-green-500)" : "var(--color-text-sub2)",
                borderRadius: "999px",
                padding: "5px 13px",
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {option.label}
            </Box>
          ))}
        </Box>
      </Box>

      {proposals.length === 0 ? (
        <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>
          {status === "pending"
            ? "確認待ちの課題案はありません。新入社員を選んで「課題案をつくる」を押してください。"
            : "該当する課題案はありません。"}
        </Box>
      ) : (
        <TableContainer>
          <Table sx={{ width: "100%", borderCollapse: "collapse" }}>
            <TableHead>
              <TableRow>
                <TableCell sx={headerCellSx}>対象者</TableCell>
                <TableCell sx={headerCellSx}>タイトル</TableCell>
                <TableCell sx={headerCellSx}>ねらい</TableCell>
                <TableCell sx={headerCellSx}>状態</TableCell>
                <TableCell sx={headerCellSx}>作成日</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {proposals.map((proposal) => (
                <TableRow key={proposal.id}>
                  <TableCell sx={bodyCellSx}>{proposal.target.displayName}</TableCell>
                  <TableCell sx={bodyCellSx}>
                    <Box
                      component={RouterLink}
                      to={`/assignments/proposals/${proposal.id}`}
                      sx={{
                        color: "var(--color-green-500)",
                        fontWeight: 700,
                        textDecoration: "none",
                        "&:hover": { textDecoration: "underline" },
                      }}
                    >
                      {proposal.title}
                    </Box>
                  </TableCell>
                  <TableCell sx={bodyCellSx}>{proposal.aim}</TableCell>
                  <TableCell sx={bodyCellSx}>
                    <Tag label={proposalStatusLabel(proposal.status)} tone={proposalStatusTone(proposal.status)} />
                  </TableCell>
                  <TableCell sx={bodyCellSx}>{proposal.createdAt.slice(0, 10)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </div>
  );
}
