import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { apiClient } from "../../lib/apiClient";
import { AgentJobQueue } from "./AgentJobQueue";
vi.mock("../../lib/apiClient", () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => vi.resetAllMocks());
const job = { id: 1, userId: 2, kind: "strength", status: "pending" };

it("対象外では取得せず、手動モードと空キューを表示", async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ provider: "manual", jobs: [] });
  const view = render(<AgentJobQueue enabled={false} />);
  expect(apiClient.get).not.toHaveBeenCalled();
  view.rerender(<AgentJobQueue enabled />);
  await screen.findByText(/解析は手動実行です/);
  expect(screen.getByText("処理待ちはありません。")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "解析状況を更新" }));
  expect(apiClient.get).toHaveBeenCalledTimes(2);
});

it("自動処理の待機・実行中・再試行待ちを識別し、更新を受け取る", async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ provider: "openai", jobs: [job,
    { ...job, id: 2, kind: "proposal", processing: true, attempts: 1 },
    { ...job, id: 3, kind: "proposal_initial", attempts: 2, lastError: "provider_unavailable" },
  ] });
  render(<AgentJobQueue enabled />);
  await screen.findByText(/解析は自動で進みます/);
  expect(screen.getByText("解析待ち")).toBeInTheDocument();
  expect(screen.getByText(/解析中.*1回/)).toBeInTheDocument();
  expect(screen.getByText(/再試行待ち.*2回/)).toBeInTheDocument();
  expect(screen.getByText("生成サービスに接続できませんでした。")).toBeInTheDocument();
  vi.mocked(apiClient.get).mockResolvedValue({ provider: "openai", jobs: [] });
  await act(async () => document.dispatchEvent(new Event("visibilitychange")));
  expect(screen.getByText("処理待ちはありません。")).toBeInTheDocument();
});

it("失敗したジョブを再試行し、二重送信を防ぐ", async () => {
  vi.mocked(apiClient.get).mockResolvedValue({ provider: "openai", jobs: [
    { ...job, status: "failed", attempts: 3, lastError: "unknown" },
  ] });
  let finish!: (value: unknown) => void;
  vi.mocked(apiClient.post).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  render(<AgentJobQueue enabled />);
  await screen.findByText(/処理に失敗しました/);
  expect(screen.getByText(/設定と入力資料を確認してください/)).toBeInTheDocument();
  const button = screen.getByRole("button", { name: "解析 #1 を再試行" });
  fireEvent.click(button); expect(button).toBeDisabled(); fireEvent.click(button);
  expect(apiClient.post).toHaveBeenCalledTimes(1);
  expect(apiClient.post).toHaveBeenCalledWith("/api/development/jobs/1/retry", {});
  vi.mocked(apiClient.get).mockResolvedValue({ provider: "openai", jobs: [] });
  await act(async () => finish({}));
  expect(screen.getByText("処理待ちはありません。")).toBeInTheDocument();
});

it("読み込み失敗・再試行失敗を表示して入力を失わない", async () => {
  vi.mocked(apiClient.get).mockRejectedValueOnce(new Error());
  render(<AgentJobQueue enabled />);
  await screen.findByText(/読み込みに失敗/);
  vi.mocked(apiClient.get).mockResolvedValue({ provider: "openai", jobs: [
    { ...job, status: "failed", lastError: "invalid_result" },
  ] });
  fireEvent.click(screen.getByRole("button", { name: "解析状況を更新" }));
  await screen.findByText("生成結果の引用や形式を確認できませんでした。");
  vi.mocked(apiClient.post).mockRejectedValue(new Error());
  fireEvent.click(screen.getByRole("button", { name: "解析 #1 を再試行" }));
  await screen.findByText(/保存できませんでした/);
  expect(screen.getByRole("button", { name: "解析 #1 を再試行" })).toBeEnabled();
});
