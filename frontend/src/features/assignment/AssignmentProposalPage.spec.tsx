import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "@mui/material/styles";

import { AssignmentProposalPage } from "./AssignmentProposalPage";
import { useAuth } from "../../components/auth/AuthProvider";
import { apiClient } from "../../lib/apiClient";
import type { ProposalDetail, ProposalProgress } from "../../lib/types";
import { createAppTheme } from "../../theme";

vi.mock("../../components/auth/AuthProvider", () => ({ useAuth: vi.fn() }));
vi.mock("../../components/layout/PageContainer", () => ({
  PageContainer: ({ children }: { children: ReactNode }) => <main>{children}</main>,
}));
vi.mock("../../lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/apiClient")>();
  return { ...actual, apiClient: { ...actual.apiClient, get: vi.fn(), post: vi.fn(), del: vi.fn() } };
});

const progress: ProposalProgress = {
  submittedCount: 3,
  reviewedCount: 1,
  notSubmittedCount: 0,
  recentMoods: [],
};

const baseProposal: ProposalDetail = {
  id: 10,
  target: { id: 2, displayName: "受講者" },
  title: "タイトル",
  aim: "ねらい",
  status: "pending",
  createdAt: "2026-09-24T00:00:00Z",
  decidedAt: null,
  body: "課題文",
  messageForMember: null,
  rationale: "理由",
  estimateMinutes: 20,
  materials: [],
  progress,
  generator: "rule_based_v1",
  assignmentId: null,
  rejectReason: null,
  decidedBy: null,
  edited: false,
};

const noReports = "課題案の生成時点で、提出済みの日報はありません";
const noMoodSelection = "提出済みの日報に、きもちの選択はありません";
const noMoodRecord = "きもちの選択記録はありません";

async function renderProposal(overrides: Partial<ProposalProgress>) {
  vi.mocked(useAuth).mockReturnValue({
    status: "authenticated",
    user: { id: 1, loginId: "trainer", displayName: "講師", role: "admin" },
    loggedOutByUser: false,
    login: vi.fn(),
    logout: vi.fn(),
  });
  const proposal = { ...baseProposal, progress: { ...progress, ...overrides } };
  vi.mocked(apiClient.get).mockImplementation(async (path) => {
    if (path === "/api/assignment-proposals/10") return proposal;
    if (path === "/api/assignment-proposals/10/revisions") return { revisions: [] };
    throw new Error(`unexpected path: ${path}`);
  });
  render(
    <ThemeProvider theme={createAppTheme("light")}>
      <MemoryRouter initialEntries={["/assignments/proposals/10"]}>
        <Routes>
          <Route path="/assignments/proposals/:proposalId" element={<AssignmentProposalPage />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  );
  const moodHeading = await screen.findByText("直近のきもち");
  // テーマの分析材料件数や課題の提出数では、きもちの空状態を推測しない。
  expect(screen.getByText("分析した材料 0件")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "この内容で配信する" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "見送る" })).toBeEnabled();
  return moodHeading.parentElement?.textContent;
}

describe("課題案の確認画面の直近のきもち", () => {
  afterEach(() => vi.clearAllMocks());

  it.each<{ overrides: Partial<ProposalProgress>; message: string }>([
    { overrides: { recentReportCount: 0, submittedCount: 3 }, message: noReports },
    { overrides: { recentReportCount: 1, submittedCount: 0 }, message: noMoodSelection },
    { overrides: { recentReportCount: 5, submittedCount: 0 }, message: noMoodSelection },
    { overrides: {}, message: noMoodRecord },
    { overrides: { recentReportCount: null }, message: noMoodRecord },
  ])("日報の件数($overrides)と記録有無に応じた空状態を表示する", async ({ overrides, message }) => {
    expect(await renderProposal(overrides)).toBe(`直近のきもち${message}`);
  });

  it.each<Partial<ProposalProgress>>([
    { recentReportCount: 4 },
    {},
    { recentReportCount: null },
  ])("きもちの記録がある場合は新旧を問わず従来のラベル・記録の順序を表示する (%j)", async (overrides) => {
    expect(await renderProposal({
      ...overrides, recentMoods: ["tired", "happy", "tired", "fun"],
    })).toBe("直近のきもちつかれたうれしいつかれたたのしい");
  });
});
