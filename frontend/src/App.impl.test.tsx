import { afterEach, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import App from "./App";
import { ApiError, apiClient } from "./lib/apiClient";

const { homeRequested, reportRequested, homeReady, resolveHome } = vi.hoisted(() => {
  let resolveHome!: () => void;
  const homeReady = new Promise<void>((resolve) => { resolveHome = resolve; });
  return { homeRequested: vi.fn(), reportRequested: vi.fn(), homeReady, resolveHome };
});

vi.mock("./lib/apiClient", async (importOriginal) => ({
  ...await importOriginal<typeof import("./lib/apiClient")>(),
  apiClient: { get: vi.fn(), post: vi.fn(), del: vi.fn() },
}));

vi.mock("./features/home/HomePage", async () => {
  homeRequested();
  await homeReady;
  const { Link, useLocation } = await import("react-router-dom");
  function HomePage() {
    const { pathname, search, hash } = useLocation();
    return <>
      <h1>ホーム</h1>
      <p>{pathname + search + hash}</p>
      <Link to="/report">日報へ</Link>
    </>;
  }
  return { HomePage };
});

vi.mock("./features/report/ReportPage", () => {
  reportRequested();
  return { ReportPage: () => <h1>日報</h1> };
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

it("保護画面は認証後に遅延読み込みし、元のURLと別画面への遷移を保持する", async () => {
  vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({
    matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn(),
  }));
  window.history.replaceState(null, "", "/home?tab=strengths#top");
  vi.mocked(apiClient.get).mockRejectedValue(new ApiError(401, "not authenticated"));
  vi.mocked(apiClient.post).mockResolvedValue({
    id: 1, loginId: "test-member", displayName: "テストユーザー", role: "member",
  });

  render(<App />);

  const loginButton = await screen.findByRole("button", { name: "ログイン" });
  expect(homeRequested).not.toHaveBeenCalled();
  expect(reportRequested).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("ログインID"), { target: { value: "test-member" } });
  fireEvent.change(screen.getByLabelText("パスワード"), { target: { value: "test-password" } });
  fireEvent.click(loginButton);

  expect(await screen.findByRole("status")).toHaveTextContent("読み込み中…");
  expect(window.location.pathname).toBe("/home");
  expect(reportRequested).not.toHaveBeenCalled();

  await act(async () => { resolveHome(); });
  expect(await screen.findByRole("heading", { name: "ホーム" })).toBeInTheDocument();
  expect(screen.getByText("/home?tab=strengths#top")).toBeInTheDocument();
  expect(homeRequested).toHaveBeenCalledTimes(1);

  fireEvent.click(screen.getByRole("link", { name: "日報へ" }));
  expect(await screen.findByRole("heading", { name: "日報" })).toBeInTheDocument();
  expect(reportRequested).toHaveBeenCalledTimes(1);
  expect(window.location.pathname).toBe("/report");
});
