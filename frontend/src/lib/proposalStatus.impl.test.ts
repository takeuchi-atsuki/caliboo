import { describe, it, expect } from "vitest";

import {
  proposalMaterialKindLabel,
  proposalMaterialKindTone,
  proposalStatusLabel,
  proposalStatusTone,
} from "./proposalStatus";
import type { ProposalMaterialKind, ProposalStatus } from "./types";

describe("proposalStatus(内部実装: 色トーン・未知値のフォールバック)", () => {
  it("状態に色トーンが対応づく", () => {
    expect(proposalStatusTone("pending")).toBe("orange");
    expect(proposalStatusTone("approved")).toBe("green");
    expect(proposalStatusTone("rejected")).toBe("blue");
  });

  it("未知の状態はそのまま返し、色トーンは既定値になる", () => {
    const unknown = "unknown" as ProposalStatus;

    expect(proposalStatusLabel(unknown)).toBe("unknown");
    expect(proposalStatusTone(unknown)).toBe("orange");
  });

  it("材料種別に色トーンが対応づく", () => {
    expect(proposalMaterialKindTone("report")).toBe("purple");
    expect(proposalMaterialKindTone("feedback")).toBe("green");
    expect(proposalMaterialKindTone("mood")).toBe("orange");
    expect(proposalMaterialKindTone("progress")).toBe("blue");
  });

  it("未知の材料種別はそのまま返し、色トーンは既定値になる", () => {
    const unknown = "unknown" as ProposalMaterialKind;

    expect(proposalMaterialKindLabel(unknown)).toBe("unknown");
    expect(proposalMaterialKindTone(unknown)).toBe("purple");
  });
});
