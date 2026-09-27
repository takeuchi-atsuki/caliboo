import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { RequireAuth } from "./RequireAuth";
import { useAuth } from "./AuthProvider";
import type { CurrentUser } from "../../lib/types";

vi.mock("./AuthProvider", () => ({
  useAuth: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);

const member: CurrentUser = { id: 1, loginId: "yuki", displayName: "ユウキ", role: "member" };

function authValue(
  status: "loading" | "authenticated" | "unauthenticated",
  user: CurrentUser | null = null,
  loggedOutByUser = false,
) {
  return { status, user, loggedOutByUser, login: vi.fn(), logout: vi.fn() };
}

function FromLocationProbe() {
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string; search: string; hash: string } } | null)?.from;
  return <span data-testid="from">{from ? `${from.pathname}${from.search}${from.hash}` : ""}</span>;
}

function renderAt(initialPath: string, loginElement = <div>ログイン画面</div>) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={loginElement} />
        <Route
          path="/secret"
          element={
            <RequireAuth>
              <div>保護されたページ</div>
            </RequireAuth>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RequireAuth", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("statusがloadingのとき何も描画しない", () => {
    mockedUseAuth.mockReturnValue(authValue("loading"));

    const { container } = renderAt("/secret");

    expect(container).toBeEmptyDOMElement();
  });

  it("statusがunauthenticatedのとき/loginへリダイレクトする", () => {
    mockedUseAuth.mockReturnValue(authValue("unauthenticated"));

    renderAt("/secret");

    expect(screen.getByText("ログイン画面")).toBeInTheDocument();
    expect(screen.queryByText("保護されたページ")).not.toBeInTheDocument();
  });

  it("statusがauthenticatedのとき子要素を描画する", () => {
    mockedUseAuth.mockReturnValue(authValue("authenticated", member));

    renderAt("/secret");

    expect(screen.getByText("保護されたページ")).toBeInTheDocument();
  });

  it("unauthenticatedのとき、元のパスをstate.fromとして/loginへ渡す", () => {
    mockedUseAuth.mockReturnValue(authValue("unauthenticated"));

    renderAt("/secret", <FromLocationProbe />);

    expect(screen.getByTestId("from").textContent).toBe("/secret");
  });

  it("unauthenticatedのとき、元のクエリ文字列・ハッシュもstate.fromとして/loginへ渡す", () => {
    mockedUseAuth.mockReturnValue(authValue("unauthenticated"));

    renderAt("/secret?tab=review#top", <FromLocationProbe />);

    expect(screen.getByTestId("from").textContent).toBe("/secret?tab=review#top");
  });

  it("利用者自身のログアウトでunauthenticatedになったときは、クエリ文字列・ハッシュを含めて元のパスを/loginへ渡さない", () => {
    mockedUseAuth.mockReturnValue(authValue("unauthenticated", null, true));

    renderAt("/secret?tab=review#top", <FromLocationProbe />);

    expect(screen.getByTestId("from").textContent).toBe("");
  });
});
