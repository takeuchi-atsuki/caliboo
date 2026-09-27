import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { LoginPage } from "./LoginPage";
import { useAuth } from "../../components/auth/AuthProvider";
import type { CurrentUser } from "../../lib/types";

vi.mock("../../components/auth/AuthProvider", () => ({
  useAuth: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);

const member: CurrentUser = { id: 1, loginId: "yuki", displayName: "ユウキ", role: "member" };

function authValue(status: "loading" | "authenticated" | "unauthenticated") {
  return {
    status,
    user: status === "authenticated" ? member : null,
    loggedOutByUser: false,
    login: vi.fn(),
    logout: vi.fn(),
  };
}

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="location">{`${location.pathname}${location.search}${location.hash}`}</span>;
}

function renderWithFrom(from?: { pathname: string; search?: string; hash?: string }) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/login", state: from ? { from } : undefined }]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/home" element={<LocationProbe />} />
        <Route path="/assignment/1" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("authenticatedのとき、state.fromのクエリ文字列・ハッシュを含めて元の画面へ遷移する", () => {
    mockedUseAuth.mockReturnValue(authValue("authenticated"));

    renderWithFrom({ pathname: "/assignment/1", search: "?tab=review", hash: "#top" });

    expect(screen.getByTestId("location").textContent).toBe("/assignment/1?tab=review#top");
  });

  it("state.fromが無いとき、authenticatedなら/homeへ遷移する", () => {
    mockedUseAuth.mockReturnValue(authValue("authenticated"));

    renderWithFrom(undefined);

    expect(screen.getByTestId("location").textContent).toBe("/home");
  });

  it("unauthenticatedのときはログインフォームを表示する", () => {
    mockedUseAuth.mockReturnValue(authValue("unauthenticated"));

    renderWithFrom({ pathname: "/assignment/1" });

    expect(screen.getByText("ログインして始めよう")).toBeInTheDocument();
  });
});
