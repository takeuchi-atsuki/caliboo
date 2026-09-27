import { describe, it, expect } from "vitest";

import {
  STRENGTH_STATUS_OPTIONS,
  confidencePercent,
  evidenceSourceLabel,
  learningDeltaIcon,
  learningDeltaLabel,
  overallStatusLabel,
  strengthStatusLabel,
  strengthStatusTone,
} from "./strengthStatus";
import type { StrengthStatus } from "./types";

describe("strengthStatus", () => {
  it("3つの判定ステータスにラベルと色トーンが対応づく", () => {
    expect(STRENGTH_STATUS_OPTIONS.map((option) => option.value)).toEqual([
      "confirmed",
      "tentative",
      "insufficient_evidence",
    ]);
    expect(strengthStatusLabel("confirmed")).toBe("確定");
    expect(strengthStatusLabel("tentative")).toBe("暫定");
    expect(strengthStatusLabel("insufficient_evidence")).toBe("評価保留");
    expect(strengthStatusTone("confirmed")).toBe("green");
    expect(strengthStatusTone("insufficient_evidence")).toBe("blue");
  });

  it("未知のステータスはそのまま返し、色トーンは既定値になる", () => {
    const unknown = "unknown" as StrengthStatus;

    expect(strengthStatusLabel(unknown)).toBe("unknown");
    expect(strengthStatusTone(unknown)).toBe("blue");
  });

  it("全体判定に説明文が対応づく", () => {
    expect(overallStatusLabel("complete")).toBe("すべての強みで根拠が揃っています");
    expect(overallStatusLabel("partial")).toBe("一部の強みは根拠が不足しています");
    expect(overallStatusLabel("insufficient")).toBe("断定できる強みはまだありません");
  });

  it("確信度(0..1)をゲージ用の百分率へ四捨五入して変換する", () => {
    expect(confidencePercent(0.85)).toBe(85);
    expect(confidencePercent(0.6)).toBe(60);
    expect(confidencePercent(0.35)).toBe(35);
    expect(confidencePercent(0.355)).toBe(36);
  });

  it("学習アジリティの向きにラベルとアイコンが対応づく", () => {
    expect(learningDeltaLabel("+")).toBe("伸びている");
    expect(learningDeltaLabel("0")).toBe("横ばい");
    expect(learningDeltaLabel("-")).toBe("言及が減っている");
    expect(learningDeltaIcon("+")).toBe("ph-bold ph-trend-up");
    expect(learningDeltaIcon("-")).toBe("ph-bold ph-trend-down");
    expect(learningDeltaIcon("0")).toBe("ph-bold ph-minus");
  });

  it("根拠の出どころを、種別・周回・レビュー職種を含む読める文字列にする", () => {
    expect(
      evidenceSourceLabel({ kind: "trajectory", iteration: 2, field: "workerOutput" }),
    ).toBe("作業ログ / 2周目 / workerOutput");
    expect(evidenceSourceLabel({ kind: "diary", field: "kpt.keep" })).toBe("日報 / kpt.keep");
    expect(evidenceSourceLabel({ kind: "review", field: "comment", role: "gamma" })).toBe(
      "レビュー / シニアエンジニア / comment",
    );
  });

  it("未知の種別・職種はそのまま表示する", () => {
    expect(evidenceSourceLabel({ kind: "other", field: "x", role: "delta" })).toBe(
      "other / delta / x",
    );
  });
});
