import { describe, it, expect } from "vitest";

import { PROPOSAL_STATUS_OPTIONS, normalizeProposalStatus, proposalMaterialKindLabel, proposalStatusLabel } from "./proposalStatus";

describe("proposalStatus", () => {
  it("3つの状態にラベルが対応づく(docs/screens/assignment.md「確認待ち/配信済み/見送り」)", () => {
    expect(PROPOSAL_STATUS_OPTIONS.map((option) => option.value)).toEqual(["pending", "approved", "rejected"]);
    expect(proposalStatusLabel("pending")).toBe("確認待ち");
    expect(proposalStatusLabel("approved")).toBe("配信済み");
    expect(proposalStatusLabel("rejected")).toBe("見送り");
  });

  it("URLのstatusパラメータが未指定・不正な場合は確認待ちに丸める(docs/screens/assignment.md「既定は確認待ち」)", () => {
    expect(normalizeProposalStatus(null)).toBe("pending");
    expect(normalizeProposalStatus("")).toBe("pending");
    expect(normalizeProposalStatus("unknown")).toBe("pending");
  });

  it("URLのstatusパラメータが既知の値の場合はそのまま使う", () => {
    expect(normalizeProposalStatus("pending")).toBe("pending");
    expect(normalizeProposalStatus("approved")).toBe("approved");
    expect(normalizeProposalStatus("rejected")).toBe("rejected");
  });

  it("材料種別にラベルが対応づく(docs/screens/assignment.md「分析した材料(日報・講師フィードバックからの引用と日付)」)", () => {
    expect(proposalMaterialKindLabel("report")).toBe("日報");
    expect(proposalMaterialKindLabel("feedback")).toBe("講師フィードバック");
    expect(proposalMaterialKindLabel("mood")).toBe("きもち");
    expect(proposalMaterialKindLabel("progress")).toBe("課題の進捗");
  });
});
