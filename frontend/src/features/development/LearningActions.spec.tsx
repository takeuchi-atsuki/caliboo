import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { apiClient } from "../../lib/apiClient";
import type { LearningAction, StrengthCandidate } from "../../lib/types";
import { LearningActions } from "./LearningActions";
vi.mock("../../lib/apiClient", () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
const candidate = { id: 4, label: "確認力", growthAction: "観点を共有する", status: "approved" } as StrengthCandidate;
const action: LearningAction = {
  id: 1, userId: 1, candidateId: 4, strengthSnapshot: { label: "確認力", growthAction: "観点を共有する" },
  title: "共有会", successCriteria: "改善案をもらう", dueDate: "2026-10-01", status: "planned",
  reflection: "", revision: 1, createdAt: "today", updatedAt: "today",
};
let data: { actions: LearningAction[]; assignments: unknown[] };
beforeEach(() => {
  vi.resetAllMocks(); data = { actions: [], assignments: [] };
  vi.mocked(apiClient.get).mockImplementation(async () => data);
  vi.mocked(apiClient.post).mockResolvedValue({});
});
function page(admin = false, target = "", candidates = [candidate]) {
  return <MemoryRouter><LearningActions admin={admin} target={target} candidates={candidates} /></MemoryRouter>;
}
function fill(label: string, value: string) { fireEvent.change(screen.getByLabelText(label, { exact: false }), { target: { value } }); }
function select(label: string, option: string) {
  fireEvent.mouseDown(screen.getByRole("combobox", { name: label }));
  fireEvent.click(screen.getByRole("option", { name: option }));
}
async function loaded() { await screen.findByText("配信された課題はありません。"); }
it("本人がヒントを編集し、達成条件と期限を決める", async () => {
  render(page()); await loaded();
  expect(screen.getByRole("button", { name: "この行動を始める" })).toBeDisabled();
  select("参考にする強み（任意）", "確認力");
  expect(screen.getByLabelText("次に取り組むこと", { exact: false })).toHaveValue("観点を共有する");
  fill("次に取り組むこと", "明日の共有会"); fill("達成の目安", "改善案を一つもらう"); fill("期限（任意）", "2026-10-01");
  fireEvent.click(screen.getByRole("button", { name: "この行動を始める" })); await screen.findByText("次の一歩を保存しました。");
  expect(apiClient.post).toHaveBeenCalledWith("/api/development/actions", {
    title: "明日の共有会", successCriteria: "改善案を一つもらう", dueDate: "2026-10-01", candidateId: 4,
  });
  expect(screen.getByLabelText("次に取り組むこと", { exact: false })).toHaveValue("");
});
it("自由入力・期限なし、保存失敗時には入力を保持", async () => {
  vi.mocked(apiClient.post).mockRejectedValueOnce(new Error()); render(page()); await loaded();
  select("参考にする強み（任意）", "確認力"); select("参考にする強み（任意）", "自分で入力する");
  fill("次に取り組むこと", "自由な挑戦"); fill("達成の目安", "試して振り返る");
  fireEvent.click(screen.getByRole("button", { name: "この行動を始める" })); await screen.findByText(/保存できませんでした/);
  expect(screen.getByLabelText("次に取り組むこと", { exact: false })).toHaveValue("自由な挑戦");
  expect(apiClient.post).toHaveBeenCalledWith("/api/development/actions", {
    title: "自由な挑戦", successCriteria: "試して振り返る", candidateId: null, dueDate: null,
  });
});
it("強みが更新されても入力を消さない", async () => {
  const view = render(page()); await loaded(); select("参考にする強み（任意）", "確認力"); fill("次に取り組むこと", "編集中");
  view.rerender(page(false, "", []));
  expect(screen.getByLabelText("次に取り組むこと", { exact: false })).toHaveValue("編集中");
  expect(screen.getByRole("combobox", { name: "参考にする強み（任意）" })).toHaveTextContent("選び直してください");
});
it("行動を編集し、振り返りを記録して完了する", async () => {
  data.actions = [action]; render(page()); await loaded();
  fireEvent.click(screen.getByRole("button", { name: "行動を編集・振り返る" }));
  fill("行動の内容", "修正した共有会"); fill("達成の目安を編集", "具体案を得る"); fill("期限を編集", "");
  select("取り組み状況", "完了"); expect(screen.getByRole("button", { name: "変更を保存" })).toBeDisabled();
  fill("振り返り", "具体的な観点を追加できた"); fireEvent.click(screen.getByRole("button", { name: "変更を保存" }));
  await waitFor(() => expect(screen.queryByLabelText("行動の内容", { exact: false })).not.toBeInTheDocument());
  expect(apiClient.post).toHaveBeenCalledWith("/api/development/actions/1", expect.objectContaining({
    title: "修正した共有会", successCriteria: "具体案を得る", dueDate: null, status: "completed", revision: 1, reflection: "具体的な観点を追加できた",
  }));
});
it("保存失敗後も編集でき、閉じて読み直せる", async () => {
  data.actions = [{ ...action, dueDate: null, strengthSnapshot: null, reflection: "前の振り返り" }];
  vi.mocked(apiClient.post).mockRejectedValue(new Error()); render(page()); await loaded();
  expect(screen.getByText("振り返り: 前の振り返り")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "行動を編集・振り返る" })); fill("期限を編集", "2026-10-03");
  fireEvent.click(screen.getByRole("button", { name: "変更を保存" })); await screen.findByText(/保存できませんでした/);
  expect(screen.getByLabelText("期限を編集")).toHaveValue("2026-10-03");
  fireEvent.click(screen.getByRole("button", { name: "編集を閉じる" })); expect(screen.queryByLabelText("期限を編集")).not.toBeInTheDocument();
});
it("自動更新で課題が届き、古い版で編集中の文章を保護する", async () => {
  data.actions = [action]; render(page()); await loaded();
  fireEvent.click(screen.getByRole("button", { name: "行動を編集・振り返る" })); fill("行動の内容", "自分の下書き");
  data = { actions: [{ ...action, revision: 2, title: "別画面で更新" }], assignments: [
    { id: 8, title: "個別の課題", status: "not_submitted", target: { id: 1 } },
    { id: 9, title: "全員の課題", status: "reviewed", target: null },
  ] };
  await act(async () => document.dispatchEvent(new Event("visibilitychange"))); await screen.findByText(/別の画面で更新されました/);
  expect(screen.getByLabelText("行動の内容", { exact: false })).toHaveValue("自分の下書き");
  expect(screen.getByRole("button", { name: "変更を保存" })).toBeDisabled();
  expect(screen.getByRole("link", { name: "個別の課題" })).toHaveAttribute("href", "/assignment/8");
  fireEvent.click(screen.getByRole("button", { name: "編集を閉じる" })); fireEvent.click(screen.getByRole("button", { name: "行動を編集・振り返る" }));
  expect(screen.getByLabelText("行動の内容", { exact: false })).toHaveValue("別画面で更新");
});
it("講師は対象者を選んで閲覧する", async () => {
  const view = render(page(true)); expect(apiClient.get).not.toHaveBeenCalled(); data.actions = [action];
  view.rerender(page(true, "1")); await loaded();
  expect(apiClient.get).toHaveBeenCalledWith("/api/development/actions?userId=1"); expect(screen.getByText("共有会")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "この行動を始める" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "行動を編集・振り返る" })).not.toBeInTheDocument();
});
