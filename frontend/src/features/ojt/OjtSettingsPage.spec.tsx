import type { ReactNode } from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { useAuth } from "../../components/auth/AuthProvider";
import { apiClient, ApiError } from "../../lib/apiClient";
import type { OjtConfiguration } from "../../lib/types";
import { OjtSettingsPage } from "./OjtSettingsPage";

vi.mock("../../components/auth/AuthProvider", () => ({ useAuth: vi.fn() }));
vi.mock("../../components/layout/PageContainer", () => ({ PageContainer: ({ children }: { children: ReactNode }) => <main>{children}</main> }));
vi.mock("../../lib/apiClient", async (original) => ({
  ...await original<typeof import("../../lib/apiClient")>(),
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

let stored: OjtConfiguration;
let list: { id: string; name: string }[];
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(useAuth).mockReturnValue({
    user: { id: 1, displayName: "講師", loginId: "sensei", role: "admin" },
    status: "authenticated", loggedOutByUser: false, login: vi.fn(), logout: vi.fn(),
  });
  stored = { id: "dev", name: "開発課", icon: "ph ph-code", color: "#d6ebff", welcomeMessage: "案内",
    quickAsks: ["規約は？"], replyGuidance: "", knowledge: [{ title: "規約", description: "命名規則" }], revision: 1 };
  list = [{ id: "dev", name: "開発課" }];
  vi.mocked(apiClient.get).mockImplementation(async (path) => path.endsWith("/departments") ? { departments: [...list] } : stored);
  vi.mocked(apiClient.post).mockImplementation(async (_path, payload) => {
    stored = { ...stored, ...payload as OjtConfiguration, revision: stored.revision + 1 };
    if (!list.some((item) => item.id === stored.id)) list = [...list, { id: stored.id, name: stored.name }];
    return stored;
  });
});

function setup() {
  render(<MemoryRouter initialEntries={["/admin/ojt-settings"]}><Routes>
    <Route path="/admin/ojt-settings" element={<OjtSettingsPage />} />
    <Route path="/home" element={<p>ホームへ移動</p>} />
  </Routes></MemoryRouter>);
  return userEvent.setup();
}
async function choose(user: ReturnType<typeof userEvent.setup>, label: string, option: string) {
  await user.click(screen.getByRole("combobox", { name: label }));
  await user.click(screen.getByRole("option", { name: option }));
}
function enter(label: string, value: string) {
  fireEvent.change(screen.getByRole("textbox", { name: label }), { target: { value } });
}

it("部署を作成し、案内・質問・ナレッジの編集と削除を保存する", async () => {
  const user = setup();
  enter("部署ID", "research"); enter("部署名", "研究課"); enter("初期案内", "研究へようこそ");
  enter("回答の補足案内", "担当者へ確認する");
  await choose(user, "アイコン", "業務"); await choose(user, "色", "緑");
  await user.click(screen.getByRole("button", { name: "質問候補を追加" }));
  await user.click(screen.getByRole("button", { name: "質問候補を追加" }));
  enter("質問候補 1", "消す質問"); enter("質問候補 2", "残す質問");
  await user.click(screen.getByRole("button", { name: "質問候補 1を削除" }));
  await user.click(screen.getByRole("button", { name: "ナレッジを追加" }));
  await user.click(screen.getByRole("button", { name: "ナレッジを追加" }));
  enter("ナレッジ 1のタイトル", "消す資料"); enter("ナレッジ 1の説明", "古い説明");
  enter("ナレッジ 2のタイトル", "残す資料"); enter("ナレッジ 2の説明", "新しい説明");
  await user.click(screen.getByRole("button", { name: "ナレッジ 1を削除" }));
  await user.click(screen.getByRole("button", { name: "設定を保存" }));
  await waitFor(() => expect(screen.getByRole("textbox", { name: "部署ID" })).toBeDisabled());
  expect(apiClient.post).toHaveBeenCalledWith("/api/ojt/departments", {
    id: "research", name: "研究課", icon: "ph ph-briefcase", color: "#cdeede",
    welcomeMessage: "研究へようこそ", replyGuidance: "担当者へ確認する", quickAsks: ["残す質問"],
    knowledge: [{ title: "残す資料", description: "新しい説明" }],
  });
  expect(screen.getByText(/設定を保存しました/)).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "初期案内" })).toHaveValue("研究へようこそ");
}, 15000);

it("既存部署の更新が競合しても入力を残し、最新設定を読み直せる", async () => {
  const user = setup();
  await choose(user, "編集する部署", "開発課");
  await screen.findByDisplayValue("規約は？");
  enter("初期案内", "保存前の案内");
  vi.mocked(apiClient.post).mockRejectedValueOnce(new ApiError(409, "conflict"));
  await user.click(screen.getByRole("button", { name: "設定を保存" }));
  expect(await screen.findByText(/他の講師が設定を更新/)).toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "初期案内" })).toHaveValue("保存前の案内");
  await user.click(screen.getByRole("button", { name: /最新の設定を読み直す/ }));
  expect(await screen.findByDisplayValue("案内")).toBeInTheDocument();
  enter("初期案内", "保存する案内");
  await user.click(screen.getByRole("button", { name: "設定を保存" }));
  expect(await screen.findByText(/設定を保存しました/)).toBeInTheDocument();
  await choose(user, "編集する部署", "新しい部署を追加");
  expect(screen.getByRole("textbox", { name: "部署ID" })).toHaveValue("");
  expect(screen.queryByText(/設定を保存しました/)).not.toBeInTheDocument();
}, 15000);

it("一覧の再取得と設定の読み込み失敗から復帰できる", async () => {
  vi.mocked(apiClient.get).mockRejectedValueOnce(new Error());
  const user = setup();
  await user.click(await screen.findByRole("button", { name: "一覧を再取得" }));
  await waitFor(() => expect(apiClient.get).toHaveBeenCalledTimes(2));
  vi.mocked(apiClient.get).mockRejectedValueOnce(new Error());
  await choose(user, "編集する部署", "開発課");
  expect(await screen.findByText(/設定を取得できません/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /最新の設定を読み直す/ }));
  expect(await screen.findByDisplayValue("案内")).toBeInTheDocument();
});

it("保存中は再保存と部署切替が無効になる", async () => {
  const user = setup();
  await choose(user, "編集する部署", "開発課");
  await screen.findByDisplayValue("案内");
  let finish!: (value: OjtConfiguration) => void;
  vi.mocked(apiClient.post).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  await user.click(screen.getByRole("button", { name: "設定を保存" }));
  expect(screen.getByRole("button", { name: "保存中…" })).toBeDisabled();
  expect(screen.getByRole("combobox", { name: "編集する部署" })).toHaveAttribute("aria-disabled", "true");
  await act(async () => finish({ ...stored, revision: 2 }));
  expect(await screen.findByText(/設定を保存しました/)).toBeInTheDocument();
});

it("一般利用者の直接アクセスはホームへ戻し、管理APIを呼ばない", () => {
  vi.mocked(useAuth).mockReturnValue({ ...useAuth(), user: { id: 2, loginId: "member", displayName: "新人", role: "member" } });
  setup();
  expect(screen.getByText("ホームへ移動")).toBeInTheDocument();
  expect(apiClient.get).not.toHaveBeenCalled();
});
