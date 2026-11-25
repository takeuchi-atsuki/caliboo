import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../../App";
import { apiClient } from "../../lib/apiClient";
import { HoldoutEvaluation } from "./HoldoutEvaluation";
vi.mock("../../lib/apiClient", () => ({ apiClient: { get: vi.fn(), post: vi.fn() }, setUnauthorizedHandler: vi.fn() }));
const base = "/api/development/holdout/cases";
const casePath = `${base}/1`;
const materialsDigest = "a".repeat(64);
const legacyResult = { trace: { provider: "codex_agent", model: "synthetic", promptVersion: "test" },
  candidates: [{ skillCode: "TEST", label: "検証", confidence: 70,
    evidence: [{ materialId: "report:8:keep", quote: "比較した" }], growthAction: "共有する" }],
  notes: "合成テスト" };
const initial = { id: 1, reportId: 8, status: "labeling", materialsDigest,
  materials: { sources: [{ id: "report:8:keep", text: "比較した" }] }, labelCount: 0,
  ownLabelSubmitted: false, result: null as unknown | null,
  labels: [] as { reviewerId: number; skillCodes: string[]; comment: string; match: string | null; accepted: boolean | null; acceptanceComment: string | null }[] };
let detail = { ...initial };
beforeEach(() => {
  vi.resetAllMocks(); detail = { ...initial };
  vi.mocked(apiClient.get).mockImplementation(async (path) => path === base ? { cases: [{ id: 1, reportId: 8, status: detail.status }] } : detail);
  vi.mocked(apiClient.post).mockResolvedValue({});
});
afterEach(() => { window.history.replaceState(null, "", "/"); vi.unstubAllGlobals(); });
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

it("凍結材料とSHA-256を同じJSONで渡し、解析担当者の返却値をそのまま取り込む", async () => {
  detail = { ...detail, labelCount: 2, ownLabelSubmitted: true };
  vi.mocked(apiClient.get).mockImplementation(async (path) => {
    if (path === "/api/auth/me") return { id: 1, loginId: "fixture", displayName: "合成講師", role: "admin" };
    if (path === "/api/development/jobs") return { jobs: [], provider: "manual" };
    if (path === "/api/development/evaluations") return { evaluatedJobs: 0, requiredJobs: 20, agreement: 0, acceptance: 0, status: "insufficient_data", legacyEvaluations: 0, trace: null };
    return path === base ? { cases: [{ id: 1, reportId: 8, status: detail.status }] } : detail;
  });
  vi.stubGlobal("matchMedia", vi.fn((query: string) => ({ matches: false, media: query,
    addEventListener: vi.fn(), removeEventListener: vi.fn(), addListener: vi.fn(), removeListener: vi.fn() })));
  window.history.replaceState(null, "", "/admin/agents");
  render(<App />);
  await screen.findByRole("heading", { name: "解析管理" });
  await select();
  const exportedJson = screen.getByText("解析担当者向けの凍結材料JSON").parentElement!.querySelector("pre")!.textContent!;
  const exported = JSON.parse(exportedJson);
  expect(exported).toEqual({ materialsDigest, materials: initial.materials });
  const payload = { materialsDigest: exported.materialsDigest, result: legacyResult };
  const json = JSON.stringify(payload);
  const save = screen.getByRole("button", { name: /解析結果を固定/ });
  expect(save).toBeDisabled();
  fill("解析結果JSON", json);
  vi.mocked(apiClient.post).mockRejectedValueOnce(new Error()); fireEvent.click(save);
  await screen.findByText(/保存できません/);
  expect(screen.getByLabelText("解析結果JSON")).toHaveValue(json);
  detail = { ...detail, status: "result_ready", result: legacyResult };
  fireEvent.click(save);
  expect(apiClient.post).toHaveBeenLastCalledWith(`${casePath}/result`, payload);
  await waitFor(() => expect(screen.queryByLabelText("解析結果JSON")).not.toBeInTheDocument());
  expect(screen.getByText(/"notes": "合成テスト"/).textContent).toBe(JSON.stringify(legacyResult, null, 2));
});

it.each([
  "broken", "null", "[]", "42",
  JSON.stringify(legacyResult),
  JSON.stringify({ materialsDigest: "未記録", result: legacyResult }),
  JSON.stringify({ materialsDigest, result: null }),
])("ハッシュ付き返却JSONの入力形式が不完全な場合は入力を保持する: %s", async (json) => {
  detail = { ...detail, labelCount: 2, ownLabelSubmitted: true };
  render(<HoldoutEvaluation reviewerId={1} />); await select();
  fill("解析結果JSON", json);
  fireEvent.click(screen.getByRole("button", { name: /解析結果を固定/ }));
  await screen.findByText(/JSONの形式を確認/);
  expect(apiClient.post).not.toHaveBeenCalled();
  expect(screen.getByLabelText("解析結果JSON")).toHaveValue(json);
});

it.each([true, false])("結果を見て受容性 %s を確定しラベルを編集しない", async (accepted) => {
  detail = { ...detail, status: "result_ready", labelCount: 2, ownLabelSubmitted: true, result: legacyResult, labels: [
    { reviewerId: 1, skillCodes: ["TEST"], comment: "理由", match: "exact", accepted: null, acceptanceComment: null },
    { reviewerId: 2, skillCodes: ["PROG"], comment: "別の理由", match: "none", accepted: true, acceptanceComment: "妥当" },
  ] };
  render(<HoldoutEvaluation reviewerId={1} />); await select();
  expect(screen.queryByLabelText("判断の理由")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("解析結果JSON")).not.toBeInTheDocument();
  expect(screen.getByText(/"notes": "合成テスト"/).textContent).toBe(JSON.stringify(legacyResult, null, 2));
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
