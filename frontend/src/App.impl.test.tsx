import { afterEach, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import App from "./App";
import { ApiError, apiClient } from "./lib/apiClient";

const { homeRendered, strengthsRendered, reportRequested, reportReady, resolveReport } = vi.hoisted(() => {
  let resolveReport!: () => void;
  const reportReady = new Promise<void>((resolve) => { resolveReport = resolve; });
  return {
    homeRendered: vi.fn(), strengthsRendered: vi.fn(), reportRequested: vi.fn(),
    reportReady, resolveReport,
  };
});

vi.mock("./lib/apiClient", async (importOriginal) => ({
  ...await importOriginal<typeof import("./lib/apiClient")>(),
  apiClient: { get: vi.fn(), post: vi.fn(), del: vi.fn() },
}));

vi.mock("./features/home/HomePage", async () => {
  const { Link, useLocation } = await import("react-router-dom");
  function HomePage() {
    homeRendered();
    const { pathname, search, hash } = useLocation();
    return <>
      <h1>ホーム</h1>
      <p>{pathname + search + hash}</p>
      <Link to="/strengths">強みへ</Link>
    </>;
  }
  return { HomePage };
});

vi.mock("./features/development/DevelopmentPage", async () => {
  const { Link } = await import("react-router-dom");
  function DevelopmentPage() {
    strengthsRendered();
    return <>
      <h1>強み</h1>
      <Link to="/report">日報へ</Link>
    </>;
  }
  return { DevelopmentPage };
});

vi.mock("./features/report/ReportPage", async () => {
  reportRequested();
  await reportReady;
  return { ReportPage: () => <h1>日報</h1> };
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

it("認証を維持し、頻用画面の即時遷移とその他画面の遅延読み込みを両立する", async () => {
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
  expect(homeRendered).not.toHaveBeenCalled();
  expect(strengthsRendered).not.toHaveBeenCalled();
  expect(reportRequested).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("ログインID"), { target: { value: "test-member" } });
  fireEvent.change(screen.getByLabelText("パスワード"), { target: { value: "test-password" } });
  fireEvent.click(loginButton);

  expect(await screen.findByRole("heading", { name: "ホーム" })).toBeInTheDocument();
  expect(screen.getByText("/home?tab=strengths#top")).toBeInTheDocument();
  expect(window.location.pathname).toBe("/home");
  expect(reportRequested).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("link", { name: "強みへ" }));
  expect(screen.getByRole("heading", { name: "強み" })).toBeInTheDocument();
  expect(window.location.pathname).toBe("/strengths");
  expect(reportRequested).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("link", { name: "日報へ" }));
  expect(await screen.findByRole("status")).toHaveTextContent("読み込み中…");
  expect(window.location.pathname).toBe("/report");

  await act(async () => { resolveReport(); });
  expect(await screen.findByRole("heading", { name: "日報" })).toBeInTheDocument();
  expect(reportRequested).toHaveBeenCalledTimes(1);
});
