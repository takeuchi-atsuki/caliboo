import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  shortcuts: [
    { icon: "ph-bold ph-clipboard-text", title: "課題に取り組む", description: "課題・フィードバックを確認", to: "/assignments", tone: "orange" },
    { icon: "ph-bold ph-graduation-cap", title: "資格勉強", description: "過去問・質問", to: "/study", tone: "blue" },
    { icon: "ph-bold ph-users-three", title: "OJT", description: "AIメンターに相談", to: "/ojt", tone: "green" },
  ],
};
function renderHome() {
  return render(<ThemeProvider theme={createAppTheme("light")}><MemoryRouter><HomePage /></MemoryRouter></ThemeProvider>);
}
beforeEach(() => vi.mocked(useHomeSummary).mockReturnValue({ summary, error: null }));

describe("ホーム (docs/screens/home.md)", () => {
  it("APIの挨拶・達成率・強みと既存画面への導線を表示する", () => {
    renderHome();
    expect(screen.getByText(summary.hero.message)).toBeInTheDocument();
    expect(screen.getByText("42%")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: `${summary.certification.name}の学習度` })).toHaveAttribute("aria-valuenow", "42");
    expect(screen.getByText("課題を整理する力")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "日報を書く" })).toHaveAttribute("href", "/report");
    expect(screen.getByRole("link", { name: "学習を続ける" })).toHaveAttribute("href", "/study");
    const shortcuts = within(screen.getByRole("region", { name: "今日は何をしよう？" }));
    expect(shortcuts.getAllByRole("link")).toHaveLength(3);
    expect(shortcuts.getByRole("link", { name: /課題に取り組む/ })).toHaveAttribute("href", "/assignments");
    expect(shortcuts.getByRole("link", { name: /資格勉強/ })).toHaveAttribute("href", "/study");
    expect(shortcuts.getByRole("link", { name: /OJT/ })).toHaveAttribute("href", "/ojt");
    expect(screen.getByRole("link", { name: "強みを詳しく見る" })).toHaveAttribute("href", "/strengths");
    expect(screen.getAllByRole("link").filter((link) => link.getAttribute("href") === "/report")).toHaveLength(1);
  });

  it("情報の優先順位と見出し・キーボード操作の順序が一致する", async () => {
    const user = userEvent.setup();
    renderHome();
    expect(screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent)).toEqual([
      "今のあなたの強み", "今日のふり返り", "今日は何をしよう？", `${summary.certification.name}の学習度`,
    ]);
    for (const destination of ["/strengths", "/report", "/assignments", "/study", "/ojt", "/study"]) {
      await user.tab();
      expect(document.activeElement).toHaveAttribute("href", destination);
    }
  });

  it("強みなしは案内を表示し、架空のタグを作らない", () => {
    vi.mocked(useHomeSummary).mockReturnValue({ summary: { ...summary, strengths: [] }, error: null });
    renderHome();
    expect(screen.getByText("日報や課題から強みを見つけていきます。")).toBeInTheDocument();
    expect(screen.queryByText("課題を整理する力")).not.toBeInTheDocument();
  });

  it("承認済みの能力・仕事の傾向・旧形式を分けて、見出しと解釈をカードに表示する", () => {
    vi.mocked(useHomeSummary).mockReturnValue({ summary: { ...summary, strengths: [
      { label: "検証する力", tone: "purple", kind: "ability", summary: "複数の課題で結果を確かめた。" },
      { label: "慎重に確かめる傾向", tone: "blue", kind: "work_style", summary: "作業ごとに期待値を確認した。" },
      { label: "旧形式の強み", tone: "green" },
    ] }, error: null });
    renderHome();
    const abilities = within(screen.getByRole("region", { name: "得意な能力" }));
    const styles = within(screen.getByRole("region", { name: "性格・仕事の進め方の傾向" }));
    expect(abilities.getByText("検証する力")).toBeInTheDocument();
    expect(abilities.getByText("複数の課題で結果を確かめた。")).toBeInTheDocument();
    expect(abilities.getByText("旧形式の強み")).toBeInTheDocument();
    expect(abilities.queryByText("慎重に確かめる傾向")).not.toBeInTheDocument();
    expect(styles.getByText("慎重に確かめる傾向")).toBeInTheDocument();
    expect(styles.getByText("作業ごとに期待値を確認した。")).toBeInTheDocument();
    expect(styles.queryByText("旧形式の強み")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "強みを詳しく見る" })).toHaveAttribute("href", "/strengths");
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

it("定期取得に失敗しても前回の強みを保持する (PL-3)", () => {
  vi.mocked(useHomeSummary).mockReturnValue({ summary, error: "更新失敗" }); renderHome();
  expect(screen.getByRole("alert")).toHaveTextContent("更新失敗");
  expect(screen.getByText("課題を整理する力")).toBeInTheDocument();
});
