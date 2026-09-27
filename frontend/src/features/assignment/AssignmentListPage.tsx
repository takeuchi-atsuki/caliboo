import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import { Mascot } from "../../components/mascot/Mascot";
import { PageContainer } from "../../components/layout/PageContainer";
import { Button } from "../../components/ui/Button";
import { PhosphorIcon } from "../../components/icon/PhosphorIcon";
import { useAuth } from "../../components/auth/AuthProvider";
import { normalizeProposalStatus } from "../../lib/proposalStatus";
import type { ProposalStatus } from "../../lib/types";
import { useAssignmentList } from "./useAssignmentList";
import { useAssignmentProposals } from "./useAssignmentProposals";
import type { AssignmentProposalsNotice } from "./useAssignmentProposals";
import { AssignmentTable } from "./AssignmentTable";
import { AssignmentCreateDialog } from "./AssignmentCreateDialog";
import { AssignmentProposalPanel } from "./AssignmentProposalPanel";

type ListTab = "assignments" | "proposals";

export function AssignmentListPage() {
  const { user } = useAuth();
  const { assignments, notice, setNotice, creating, createAssignment } = useAssignmentList();
  const [createOpen, setCreateOpen] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();

  const isAdmin = user?.role === "admin";
  const tab: ListTab = isAdmin && searchParams.get("tab") === "proposals" ? "proposals" : "assignments";
  const status = normalizeProposalStatus(searchParams.get("status"));

  const {
    proposals,
    members,
    pendingCount,
    notice: proposalNotice,
    setNotice: setProposalNotice,
    generating,
    generateProposal,
  } = useAssignmentProposals(status, isAdmin);

  // !NOTE: 課題案の配信・見送り(`AssignmentProposalPage`)は完了後にこの画面へ戻るため、
  //        成功通知はここへ`navigate`のstateで引き継いで表示する(この画面自体は
  //        アンマウントされるため、課題案側のnotice状態は引き継げない)。表示後は
  //        `history.state`をreplaceで消し、リロード時に再表示されないようにする
  //        (`StudyChatPage`のlocation.state引き継ぎと同じ考え方)。
  const handoffNotice = (location.state as { notice?: AssignmentProposalsNotice } | null)?.notice ?? null;
  useEffect(() => {
    if (!handoffNotice) return;
    setProposalNotice(handoffNotice);
    navigate(`${location.pathname}${location.search}`, { replace: true, state: null });
  }, [handoffNotice, location.pathname, location.search, navigate, setProposalNotice]);

  // !NOTE: RequireAuthが未ログイン中はこのページ自体を描画しないため、通常は必ずuserが
  //        存在する。型を絞り込むためのガードで、実際に到達することは想定していない。
  if (!user) {
    return null;
  }

  const handleTabChange = (_event: unknown, next: ListTab) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (next === "proposals") {
        params.set("tab", "proposals");
        if (!params.get("status")) {
          params.set("status", "pending");
        }
      } else {
        params.delete("tab");
        params.delete("status");
      }
      return params;
    });
  };

  const handleStatusChange = (next: ProposalStatus) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set("tab", "proposals");
      params.set("status", next);
      return params;
    });
  };

  return (
    <PageContainer>
      <div style={{ padding: "var(--page-gutter)", display: "flex", flexDirection: "column", gap: 24 }}>
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            justifyContent: "space-between",
            alignItems: { xs: "flex-start", sm: "center" },
            gap: "14px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <Mascot size={46} color="var(--color-blue-300)" mood="happy" />
            <div>
              <div style={{ fontWeight: 800, fontSize: 23, color: "var(--color-text)" }}>課題演習</div>
              <div style={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>
                講師が出した課題に回答・提出しよう
              </div>
            </div>
          </div>
          {isAdmin ? (
            <Button icon="ph-bold ph-plus" onClick={() => setCreateOpen(true)}>
              課題を作成
            </Button>
          ) : null}
        </Box>

        {isAdmin ? (
          <Tabs
            value={tab}
            onChange={handleTabChange}
            sx={{
              minHeight: 0,
              borderBottom: "1.5px solid var(--color-bg-alt)",
              "& .MuiTab-root": { textTransform: "none", fontWeight: 700, minHeight: 0, padding: "10px 14px" },
              "& .MuiTab-root.Mui-selected": { color: "var(--color-green-500)" },
              "& .MuiTabs-indicator": { backgroundColor: "var(--color-green-400)" },
            }}
          >
            <Tab value="assignments" label="配信中の課題" />
            <Tab
              value="proposals"
              label={
                <Box sx={{ display: "flex", alignItems: "center", gap: "7px" }}>
                  <PhosphorIcon name="ph-bold ph-sparkle" size={14} />
                  AIの課題案
                  {pendingCount > 0 ? (
                    <Box
                      component="span"
                      sx={{
                        minWidth: 20,
                        height: 20,
                        padding: "0 6px",
                        borderRadius: "10px",
                        display: "inline-grid",
                        placeItems: "center",
                        fontSize: 11.5,
                        fontWeight: 800,
                        background: "var(--color-pink-400)",
                        color: "var(--color-panel)",
                      }}
                    >
                      {pendingCount}
                    </Box>
                  ) : null}
                </Box>
              }
            />
          </Tabs>
        ) : null}

        {notice ? (
          <Alert severity={notice.severity} onClose={() => setNotice(null)}>
            {notice.message}
          </Alert>
        ) : null}

        {tab === "proposals" ? (
          <AssignmentProposalPanel
            status={status}
            onStatusChange={handleStatusChange}
            proposals={proposals}
            members={members}
            notice={proposalNotice}
            setNotice={setProposalNotice}
            generating={generating}
            generateProposal={generateProposal}
          />
        ) : (
          <div style={{ background: "var(--color-panel)", borderRadius: 20, padding: "20px 22px" }}>
            <AssignmentTable
              items={assignments}
              showStatusColumn={!isAdmin}
              showTargetColumn={isAdmin}
              currentUserId={user.id}
            />
          </div>
        )}
      </div>

      <AssignmentCreateDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        submitting={creating}
        onCreate={createAssignment}
      />
    </PageContainer>
  );
}
