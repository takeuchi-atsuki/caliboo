import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import type { ReactNode } from "react";

import { DevelopmentPage } from "./DevelopmentPage";
import { apiClient } from "../../lib/apiClient";
import { useAuth } from "../../components/auth/AuthProvider";
import type { StrengthCandidate } from "../../lib/types";

vi.mock("../../lib/apiClient", () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
vi.mock("../../components/auth/AuthProvider", () => ({ useAuth: vi.fn() }));
vi.mock("../../components/layout/PageContainer", () => ({ PageContainer: ({ children }: { children: ReactNode }) => <>{children}</> }));
vi.mock("./LearningActions", () => ({ LearningActions: () => <div>次の行動</div> }));

const evidence = [{ materialId: "report:1:keep", quote: "期待値と実測値を照合した。", source: { date: "2026-09-29", field: "keep" } }];
const ability: StrengthCandidate = {
  id: 1, jobId: 1, userId: 5, kind: "ability", label: "検証する力", skillCode: "TEST", confidence: 90,
  summary: "複数の課題で結果を確かめた。", scopeNote: "教材とローカル環境に限る。",
  growthAction: "別の条件でも試す。", status: "approved", evidence,
};
const style: StrengthCandidate = {
  ...ability, id: 2, kind: "work_style", label: "慎重に確かめる傾向", skillCode: "DOCM",
  summary: "作業ごとに期待値を確認した。", scopeNote: "観測した課題での傾向。",
};
let candidates: StrengthCandidate[];

beforeEach(() => {
  vi.resetAllMocks();
  candidates = [];
  vi.mocked(useAuth).mockReturnValue({ user: { id: 5, loginId: "takeuchi", displayName: "竹内", role: "member" } } as ReturnType<typeof useAuth>);
  vi.mocked(apiClient.get).mockImplementation(async (path) => path === "/api/users"
    ? { users: [{ id: 5, loginId: "takeuchi", displayName: "竹内", role: "member", active: true }] }
    : { candidates, jobs: [] });
  vi.mocked(apiClient.post).mockResolvedValue({});
});

function renderPage() { return render(<MemoryRouter><DevelopmentPage /></MemoryRouter>); }

describe("実提出データの強み画面 (docs/strength-profile.md)", () => {
  it("能力と仕事の傾向を分け、理由・範囲・次の取り組みを見せ、根拠は開いて確認する", async () => {
    candidates = [ability, style];
    renderPage();
    const abilities = within(await screen.findByRole("region", { name: "得意な能力" }));
    const styles = within(screen.getByRole("region", { name: "性格・仕事の進め方の傾向" }));
    expect(abilities.getByRole("heading", { name: ability.label })).toBeInTheDocument();
    expect(abilities.getByText(ability.summary!)).toBeInTheDocument();
    expect(abilities.getByText(`評価できる範囲: ${ability.scopeNote}`)).toBeInTheDocument();
    expect(abilities.getByText(`次の取り組み: ${ability.growthAction}`)).toBeInTheDocument();
    expect(styles.getByRole("heading", { name: style.label })).toBeInTheDocument();
    expect(styles.getByText(style.summary!)).toBeInTheDocument();
    const details = abilities.getByText("根拠を見る（1件）").closest("details")!;
    expect(details.open).toBe(false);
    await userEvent.setup().click(abilities.getByText("根拠を見る（1件）"));
    expect(details.open).toBe(true);
    expect(within(details).getByText(evidence[0].quote)).toBeVisible();
    expect(within(details).getByText(/report:1:keep/)).toBeVisible();
    await userEvent.setup().click(abilities.getByText("根拠を見る（1件）"));
    expect(details.open).toBe(false);
    expect(screen.getByText("次の行動")).toBeInTheDocument();
  });

  it("kindがない旧候補は能力に入れ、両分類が空ならそれぞれ案内する", async () => {
    candidates = [{ ...ability, kind: undefined, summary: undefined, scopeNote: undefined }];
    const view = renderPage();
    const abilities = within(await screen.findByRole("region", { name: "得意な能力" }));
    expect(abilities.getByRole("heading", { name: ability.label })).toBeInTheDocument();
    expect(screen.getByText(/表示できる仕事の傾向はまだありません/)).toBeInTheDocument();
    view.unmount();
    candidates = [];
    renderPage();
    expect(await screen.findByText(/表示できる能力はまだありません/)).toBeInTheDocument();
    expect(screen.getByText(/表示できる仕事の傾向はまだありません/)).toBeInTheDocument();
  });

  it("講師は4項目を直して傾向を承認し、理由と範囲が空なら承認できない", async () => {
    vi.mocked(useAuth).mockReturnValue({ user: { id: 1, loginId: "teacher", displayName: "講師", role: "admin" } } as ReturnType<typeof useAuth>);
    candidates = [{ ...style, status: "pending" }];
    renderPage();
    await screen.findByRole("heading", { name: style.label });
    const approve = screen.getByRole("button", { name: "承認して表示" });
    fireEvent.change(screen.getByRole("textbox", { name: "強みの解釈" }), { target: { value: "" } });
    expect(approve).toBeDisabled();
    fireEvent.change(screen.getByRole("textbox", { name: "強みの解釈" }), { target: { value: "新しい理由" } });
    fireEvent.change(screen.getByRole("textbox", { name: "評価できる範囲" }), { target: { value: "" } });
    expect(approve).toBeDisabled();
    fireEvent.change(screen.getByRole("textbox", { name: "評価できる範囲" }), { target: { value: "新しい範囲" } });
    fireEvent.change(screen.getByRole("textbox", { name: "強みの表現" }), { target: { value: "  確かめる傾向  " } });
    fireEvent.change(screen.getByRole("textbox", { name: "次の取り組み" }), { target: { value: "  条件を増やす  " } });
    expect(approve).toBeEnabled();
    fireEvent.click(approve);
    await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith("/api/development/strengths/2/decision", {
      status: "approved", label: "確かめる傾向", summary: "新しい理由", scopeNote: "新しい範囲", growthAction: "条件を増やす",
    }));
  });

  it("旧候補は解釈と範囲が空でも講師が承認できる", async () => {
    vi.mocked(useAuth).mockReturnValue({ user: { id: 1, loginId: "teacher", displayName: "講師", role: "admin" } } as ReturnType<typeof useAuth>);
    candidates = [{ ...ability, kind: undefined, summary: undefined, scopeNote: undefined, status: "pending" }];
    renderPage();
    await screen.findByRole("heading", { name: ability.label });
    fireEvent.click(screen.getByRole("button", { name: "承認して表示" }));
    await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith("/api/development/strengths/1/decision", {
      status: "approved", label: ability.label, summary: "", scopeNote: "", growthAction: ability.growthAction,
    }));
  });
});
