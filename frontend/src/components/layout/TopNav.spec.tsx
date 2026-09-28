import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { ThemeProvider } from "@mui/material/styles";
import { useMediaQuery } from "@mui/material";
import { TopNav } from "./TopNav";
import { useAuth } from "../auth/AuthProvider";
import { useThemeMode } from "../theme/ThemeModeProvider";
import { createAppTheme } from "../../theme";
import type { CurrentUser } from "../../lib/types";

vi.mock("../auth/AuthProvider", () => ({ useAuth: vi.fn(), ROLE_LABEL: { admin: "講師", member: "新入社員" } }));
vi.mock("../theme/ThemeModeProvider", () => ({ useThemeMode: vi.fn() }));
vi.mock("@mui/material", async (original) => ({ ...await original<typeof import("@mui/material")>(), useMediaQuery: vi.fn() }));

const member: CurrentUser = { id: 1, loginId: "member", displayName: "ユウキ", role: "member", streakDays: 7 };
const logout = vi.fn();
const toggleMode = vi.fn();

function Location() {
  return <output data-testid="location">{useLocation().pathname}</output>;
}
function renderNav(path = "/home", streakDays?: number) {
  return render(<ThemeProvider theme={createAppTheme("light")}><MemoryRouter initialEntries={[path]}>
    <TopNav streakDays={streakDays} /><Location />
  </MemoryRouter></ThemeProvider>);
}
function setUser(user: CurrentUser | null) {
  vi.mocked(useAuth).mockReturnValue({ user, status: user ? "authenticated" : "unauthenticated", loggedOutByUser: false, login: vi.fn(), logout });
}

beforeEach(() => {
  vi.clearAllMocks();
  setUser(member);
  vi.mocked(useThemeMode).mockReturnValue({ mode: "light", toggleMode });
  vi.mocked(useMediaQuery).mockReturnValue(false);
});

describe("共通ナビゲーション (docs/ui-refresh.md)", () => {
  it("詳細URLでも親を現在地とし、下部リンクで遷移できる", async () => {
    const user = userEvent.setup();
    renderNav("/assignments/42");
    const mobile = within(screen.getByLabelText("モバイルナビゲーション"));
    expect(mobile.getByRole("link", { name: "課題" })).toHaveAttribute("aria-current", "page");
    expect(mobile.getByRole("link", { name: "ホーム" })).not.toHaveAttribute("aria-current");
    await user.click(mobile.getByRole("link", { name: "資格勉強" }));
    expect(screen.getByTestId("location")).toHaveTextContent("/study");
    expect(mobile.getByRole("link", { name: "資格勉強" })).toHaveAttribute("aria-current", "page");
  });

  it("その他から全機能へ移動でき、遷移時にDrawerを閉じる", async () => {
    const user = userEvent.setup();
    renderNav("/strengths/poc");
    await user.click(screen.getByRole("button", { name: "その他" }));
    const menu = within(screen.getByRole("navigation", { name: "すべてのメニュー" }));
    expect(menu.getByRole("link", { name: "強み" })).toHaveAttribute("aria-current", "page");
    expect(menu.queryByRole("link", { name: "ユーザー" })).not.toBeInTheDocument();
    expect(menu.queryByRole("link", { name: "OJT設定" })).not.toBeInTheDocument();
    await user.click(menu.getByRole("link", { name: "OJT" }));
    expect(screen.getByTestId("location")).toHaveTextContent("/ojt");
    await waitFor(() => expect(screen.queryByRole("navigation", { name: "すべてのメニュー" })).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "その他" })).toHaveAttribute("aria-expanded", "false");
  });

  it("メニューを閉じるボタンとEscで閉じ、起点にフォーカスを戻す", async () => {
    const user = userEvent.setup();
    renderNav();
    const opener = screen.getByRole("button", { name: "メニューを開く" });
    await user.click(opener);
    expect(opener).toHaveAttribute("aria-expanded", "true");
    await user.click(screen.getByRole("button", { name: "メニューを閉じる" }));
    await waitFor(() => expect(opener).toHaveFocus());
    await user.click(opener);
    await user.keyboard("{Escape}");
    await waitFor(() => expect(opener).toHaveAttribute("aria-expanded", "false"));
    expect(opener).toHaveFocus();
  });

  it("1200px以上になればDrawerを閉じ、狭めても再度開かない", async () => {
    const user = userEvent.setup();
    function Nav() { return <ThemeProvider theme={createAppTheme("light")}><MemoryRouter><TopNav /></MemoryRouter></ThemeProvider>; }
    const view = render(<Nav />);
    await user.click(screen.getByRole("button", { name: "メニューを開く" }));
    vi.mocked(useMediaQuery).mockReturnValue(true);
    view.rerender(<Nav />);
    await waitFor(() => expect(screen.queryByRole("navigation", { name: "すべてのメニュー" })).not.toBeInTheDocument());
    vi.mocked(useMediaQuery).mockReturnValue(false);
    view.rerender(<Nav />);
    expect(screen.getByRole("button", { name: "メニューを開く" })).toHaveAttribute("aria-expanded", "false");
  });

  it("講師だけに管理リンクを表示し、テーマ切替とログアウトを実行する", async () => {
    const user = userEvent.setup();
    setUser({ ...member, role: "admin" });
    vi.mocked(useThemeMode).mockReturnValue({ mode: "dark", toggleMode });
    renderNav("/admin/agents");
    expect(screen.getByText("7")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "ライトモードに切り替える" }));
    expect(toggleMode).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: "ログアウト" }));
    expect(logout).toHaveBeenCalledOnce();
    await user.click(screen.getByRole("button", { name: "その他" }));
    const menu = within(screen.getByRole("navigation", { name: "すべてのメニュー" }));
    expect(menu.getByRole("link", { name: "解析管理" })).toHaveAttribute("aria-current", "page");
    expect(menu.getByRole("link", { name: "ユーザー" })).toHaveAttribute("href", "/admin/users");
    expect(menu.getByRole("link", { name: "相談" })).toHaveAttribute("href", "/admin/ojt");
    expect(menu.getByRole("link", { name: "OJT設定" })).toHaveAttribute("href", "/admin/ojt-settings");
  });

  it("ストリークの明示値を優先し、未設定の場合は0日を表示する", () => {
    const view = renderNav("/home", 3);
    expect(screen.getByText("3")).toBeInTheDocument();
    view.unmount();
    setUser({ ...member, streakDays: undefined });
    renderNav();
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("未ログイン時はナビゲーションを表示しない", () => {
    setUser(null);
    renderNav();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });
});
