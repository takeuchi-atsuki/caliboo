import type { LearningDelta, OverallStatus, StrengthStatus, Tone } from "./types";

export const STRENGTH_STATUS_OPTIONS: { value: StrengthStatus; label: string; tone: Tone }[] = [
  { value: "confirmed", label: "確定", tone: "green" },
  { value: "tentative", label: "暫定", tone: "orange" },
  { value: "insufficient_evidence", label: "評価保留", tone: "blue" },
];

export function strengthStatusLabel(status: StrengthStatus): string {
  return STRENGTH_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

export function strengthStatusTone(status: StrengthStatus): Tone {
  return STRENGTH_STATUS_OPTIONS.find((option) => option.value === status)?.tone ?? "blue";
}

const OVERALL_STATUS_LABELS: Record<OverallStatus, string> = {
  complete: "すべての強みで根拠が揃っています",
  partial: "一部の強みは根拠が不足しています",
  insufficient: "断定できる強みはまだありません",
};

export function overallStatusLabel(status: OverallStatus): string {
  return OVERALL_STATUS_LABELS[status];
}

/**
 * 確信度(0..1)をドーナツゲージ用の百分率へ変換する。
 *
 * !NOTE: `DonutProgress`は0-100のpercentを前提にしているため、ここで四捨五入して整数化する。
 */
export function confidencePercent(confidence: number): number {
  return Math.round(confidence * 100);
}

const LEARNING_DELTA_LABELS: Record<LearningDelta, string> = {
  "+": "伸びている",
  "0": "横ばい",
  "-": "言及が減っている",
};

export function learningDeltaLabel(delta: LearningDelta): string {
  return LEARNING_DELTA_LABELS[delta];
}

export function learningDeltaIcon(delta: LearningDelta): string {
  if (delta === "+") return "ph-bold ph-trend-up";
  if (delta === "-") return "ph-bold ph-trend-down";
  return "ph-bold ph-minus";
}

const EVIDENCE_KIND_LABELS: Record<string, string> = {
  trajectory: "作業ログ",
  diary: "日報",
  review: "レビュー",
};

const EVIDENCE_ROLE_LABELS: Record<string, string> = {
  alpha: "管理職",
  beta: "講師",
  gamma: "シニアエンジニア",
};

/** 根拠の出どころを「日報 / kpt.keep」のような読める文字列へ組み立てる。 */
export function evidenceSourceLabel(source: {
  kind: string;
  iteration?: number | null;
  field: string;
  role?: string | null;
}): string {
  const kind = EVIDENCE_KIND_LABELS[source.kind] ?? source.kind;
  const parts: string[] = [kind];
  if (source.iteration) parts.push(`${source.iteration}周目`);
  if (source.role) parts.push(EVIDENCE_ROLE_LABELS[source.role] ?? source.role);
  parts.push(source.field);
  return parts.join(" / ");
}
