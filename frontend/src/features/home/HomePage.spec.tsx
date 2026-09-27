import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ThemeProvider } from "@mui/material/styles";
import type { ReactNode } from "react";

import { HomePage } from "./HomePage";
import { useHomeSummary } from "./useHomeSummary";
import { createAppTheme } from "../../theme";
import type { HomeSummary } from "../../lib/types";

vi.mock("./useHomeSummary", () => ({ useHomeSummary: vi.fn() }));
vi.mock("../../components/layout/PageContainer", () => ({ PageContainer: ({ children }: { children: ReactNode }) => <>{children}</> }));

const summary: HomeSummary = {
  user: { name: "ユウキ", streakDays: 7 },
  hero: { message: "おかえり、ユウキさん！" },
  certification: { name: "基本情報技術者試験", achievementPercent: 42 },
  strengths: [{ label: "課題を整理する力", tone: "purple" }],
  shortcuts: [{ icon: "ph ph-book-open", title: "資格勉強", description: "少しずつ学ぼう", to: "/study", tone: "blue" }],
};
function renderHome() {
  return render(<ThemeProvider theme={createAppTheme("light")}><MemoryRouter><HomePage /></MemoryRouter></ThemeProvider>);
}
beforeEach(() => vi.mocked(useHomeSummary).mockReturnValue({ summary, error: null }));

describe("ホーム (docs/screens/home.md)", () => {
  it("APIの挨拶・達成率・強みと既存画面への導線を表示する", () => {
    renderHome();
    expect(screen.getByRole("heading", { name: summary.hero.message })).toBeInTheDocument();
    expect(screen.getByText("42%")).toBeInTheDocument();
    expect(screen.getByText(summary.certification.name)).toBeInTheDocument();
    expect(screen.getByText("課題を整理する力")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "日報を書く" })).toHaveAttribute("href", "/report");
    expect(screen.getByRole("link", { name: "学習を続ける" })).toHaveAttribute("href", "/study");
    const shortcuts = within(screen.getByRole("region", { name: "今日は何をしよう？" }));
    expect(shortcuts.getByRole("link", { name: /資格勉強/ })).toHaveAttribute("href", "/study");
    expect(screen.getByRole("link", { name: "根拠と成長のヒントを見る" })).toHaveAttribute("href", "/strengths");
  });

  it("強みなしは案内を表示し、架空のタグを作らない", () => {
    vi.mocked(useHomeSummary).mockReturnValue({ summary: { ...summary, strengths: [] }, error: null });
    renderHome();
    expect(screen.getByText("日報や課題から強みを見つけていきます。")).toBeInTheDocument();
    expect(screen.queryByText("課題を整理する力")).not.toBeInTheDocument();
  });

  it("取得待ちはステータス、取得失敗はエラーとして通知する", () => {
    vi.mocked(useHomeSummary).mockReturnValue({ summary: null, error: null });
    const view = renderHome();
    expect(screen.getByRole("status", { name: "ホームを読み込み中" })).toBeInTheDocument();
    view.unmount();
    vi.mocked(useHomeSummary).mockReturnValue({ summary: null, error: "接続エラー" });
    renderHome();
    expect(screen.getByRole("alert")).toHaveTextContent("接続エラー");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
