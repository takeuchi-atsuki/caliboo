import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { apiClient } from "../../lib/apiClient";
import { HoldoutEvaluation } from "./HoldoutEvaluation";
vi.mock("../../lib/apiClient", () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
const base = "/api/development/holdout/cases";
const casePath = `${base}/1`;
const initial = { id: 1, reportId: 8, status: "labeling", materialsDigest: "digest",
  materials: { sources: [{ id: "report:8:keep", text: "比較した" }] }, labelCount: 0,
  ownLabelSubmitted: false, result: null as unknown | null,
  labels: [] as { reviewerId: number; skillCodes: string[]; comment: string; match: string | null; accepted: boolean | null; acceptanceComment: string | null }[] };
let detail = { ...initial };
beforeEach(() => {
  vi.resetAllMocks(); detail = { ...initial };
  vi.mocked(apiClient.get).mockImplementation(async (path) => path === base ? { cases: [{ id: 1, reportId: 8, status: detail.status }] } : detail);
  vi.mocked(apiClient.post).mockResolvedValue({});
});
function fill(label: string, value: string) { fireEvent.change(screen.getByLabelText(label), { target: { value } }); }
async function select() { fireEvent.click(await screen.findByRole("button", { name: /評価 #1/ })); await screen.findByText("report:8:keep: 比較した"); }

it("実日報確認とIDを必須にし、登録と通信失敗からの再読込を扱う", async () => {
  vi.mocked(apiClient.get).mockRejectedValueOnce(new Error());
  render(<HoldoutEvaluation reviewerId={1} />);
  await screen.findByText(/読み込みに失敗/);
  const save = screen.getByRole("button", { name: "評価材料を固定する" });
  expect(save).toBeDisabled(); fill("評価に使う提出済み日報ID", "1.5");
  fireEvent.click(screen.getByLabelText(/実日報であり/)); expect(save).toBeDisabled();
  fill("評価に使う提出済み日報ID", "rpt_20260929_8"); fireEvent.click(save);
  await screen.findByRole("button", { name: /評価 #1/ });
  expect(apiClient.post).toHaveBeenCalledWith(base, { reportId: 8, realAndUnseen: true });
  fireEvent.click(screen.getByRole("button", { name: "評価ケースを更新" }));
  vi.mocked(apiClient.get).mockRejectedValueOnce(new Error());
  fireEvent.click(screen.getByRole("button", { name: /評価 #1/ }));
  await screen.findByText(/読み込みに失敗/);
  fireEvent.click(screen.getByRole("button", { name: "選択した評価を更新" }));
  await screen.findByText("独立ラベル: 0/2名");
});

it("未閲覧確認と独立ラベルを固定し、保存中の二重操作を防ぐ", async () => {
  render(<HoldoutEvaluation reviewerId={1} />); await select();
  const save = screen.getByRole("button", { name: /独立ラベルを確定/ });
  expect(save).toBeDisabled(); fill("判断の理由", "自分の判断");
  fill("独立に判断したスキルコード（カンマ区切り、該当なしは空欄）", " TEST, ,PROG ");
  fireEvent.click(screen.getByLabelText(/解析結果や他の評価者/));
  let finish!: (value: unknown) => void;
  vi.mocked(apiClient.post).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  fireEvent.click(save); expect(save).toBeDisabled(); fireEvent.click(save);
  expect(apiClient.post).toHaveBeenCalledTimes(1);
  expect(apiClient.post).toHaveBeenCalledWith(`${casePath}/labels`, { skillCodes: ["TEST", "PROG"], comment: "自分の判断", outputUnseen: true });
  detail = { ...detail, labelCount: 1, ownLabelSubmitted: true };
  await act(async () => finish({}));
  await screen.findByText("あなたの独立ラベルは確定済みです。");
  expect(screen.queryByLabelText("判断の理由")).not.toBeInTheDocument();
});

it("2名の確定後に結果を固定し、不正JSONや保存失敗でも入力を保持する", async () => {
  detail = { ...detail, labelCount: 2, ownLabelSubmitted: true };
  render(<HoldoutEvaluation reviewerId={1} />); await select();
  const save = screen.getByRole("button", { name: /解析結果を固定/ });
  expect(save).toBeDisabled(); fill("解析結果JSON", "broken"); fireEvent.click(save);
  await screen.findByText(/JSONの形式を確認/); expect(apiClient.post).not.toHaveBeenCalled();
  fill("解析結果JSON", '{"candidates":[]}');
  vi.mocked(apiClient.post).mockRejectedValueOnce(new Error()); fireEvent.click(save);
  await screen.findByText(/保存できません/);
  expect(screen.getByLabelText("解析結果JSON")).toHaveValue('{"candidates":[]}');
  fireEvent.click(save);
  expect(apiClient.post).toHaveBeenLastCalledWith(`${casePath}/result`, { materialsDigest: "digest", result: { candidates: [] } });
  await act(async () => {});
});

it.each([true, false])("結果を見て受容性 %s を確定しラベルを編集しない", async (accepted) => {
  detail = { ...detail, status: "result_ready", labelCount: 2, ownLabelSubmitted: true, result: { candidates: [] }, labels: [
    { reviewerId: 1, skillCodes: [], comment: "理由", match: "exact", accepted: null, acceptanceComment: null },
    { reviewerId: 2, skillCodes: ["TEST"], comment: "別の理由", match: "none", accepted: true, acceptanceComment: "妥当" },
  ] };
  render(<HoldoutEvaluation reviewerId={1} />); await select();
  expect(screen.queryByLabelText("判断の理由")).not.toBeInTheDocument();
  const save = screen.getByRole("button", { name: accepted ? "受容して確定" : "改善が必要として確定" });
  expect(save).toBeDisabled(); fill("結果を確認した理由", "原文と照合した");
  detail = { ...detail, labels: detail.labels.map((label) => ({ ...label, accepted, acceptanceComment: "確定" })) };
  fireEvent.click(save);
  expect(apiClient.post).toHaveBeenCalledWith(`${casePath}/acceptance`, { accepted, comment: "原文と照合した" });
  await waitFor(() => expect(screen.queryByLabelText("結果を確認した理由")).not.toBeInTheDocument());
});

it("独立ラベルを持たない講師は確定結果を閲覧する", async () => {
  detail = { ...detail, labelCount: 2, status: "result_ready", result: { notes: "検証済み" } };
  render(<HoldoutEvaluation reviewerId={3} />); await select();
  expect(screen.queryByLabelText("判断の理由")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("結果を確認した理由")).not.toBeInTheDocument();
});
