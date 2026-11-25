import { afterEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import App from "./App";
import { ApiError, apiClient } from "./lib/apiClient";

vi.mock("./lib/apiClient", async (importOriginal) => ({
  ...await importOriginal<typeof import("./lib/apiClient")>(),
  apiClient: { get: vi.fn(), post: vi.fn(), del: vi.fn() },
}));

vi.mock("./features/home/HomePage", async () => {
  const { Link } = await import("react-router-dom");
  return { HomePage: () => <><h1>ホーム</h1><Link to="/strengths">強みへ</Link></> };
});

vi.mock("./features/development/DevelopmentPage", () => ({
  DevelopmentPage: () => <h1>強み</h1>,
}));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  window.history.replaceState(null, "", "/");
});

it("通常ビルドでは限定試用環境の注意事項を表示しない", async () => {
  vi.stubEnv("MODE", "production");
  vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({
    matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn(),
  }));
  window.history.replaceState(null, "", "/login");
  vi.mocked(apiClient.get).mockRejectedValue(new ApiError(401, "not authenticated"));
  render(<App />);
  await screen.findByRole("button", { name: "ログイン" });
  expect(screen.queryByLabelText("限定試用環境の注意事項")).not.toBeInTheDocument();
});

it("試用ビルドではログイン前後の画面に合成データ専用とデータ消失の注意事項を表示する", async () => {
  vi.stubEnv("MODE", "trial");
  vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({
    matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn(),
  }));
  window.history.replaceState(null, "", "/login");
  vi.mocked(apiClient.get).mockRejectedValue(new ApiError(401, "not authenticated"));
  vi.mocked(apiClient.post).mockResolvedValue({
    id: 1, loginId: "test-member", displayName: "テストユーザー", role: "member",
  });

  render(<App />);
  const loginButton = await screen.findByRole("button", { name: "ログイン" });
  const checkNotice = () => {
    const notice = screen.getByLabelText("限定試用環境の注意事項");
    expect(notice).toHaveTextContent("合成データ専用");
    expect(notice).toHaveTextContent("実データ・個人情報・機密情報を入力しないでください");
    expect(notice).toHaveTextContent("再起動・停止などで入力データは失われます");
  };
  checkNotice();
  fireEvent.change(screen.getByLabelText("ログインID"), { target: { value: "test-member" } });
  fireEvent.change(screen.getByLabelText("パスワード"), { target: { value: "test-password" } });
  fireEvent.click(loginButton);
  await screen.findByRole("heading", { name: "ホーム" });
  checkNotice();
  fireEvent.click(screen.getByRole("link", { name: "強みへ" }));
  expect(screen.getByRole("heading", { name: "強み" })).toBeInTheDocument();
  checkNotice();
});
