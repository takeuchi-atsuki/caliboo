import type { ProposalMaterialKind, ProposalStatus, Tone } from "./types";

export const PROPOSAL_STATUS_OPTIONS: { value: ProposalStatus; label: string; tone: Tone }[] = [
  { value: "pending", label: "確認待ち", tone: "orange" },
  { value: "approved", label: "配信済み", tone: "green" },
  { value: "rejected", label: "見送り", tone: "blue" },
];

export function proposalStatusLabel(status: ProposalStatus): string {
  return PROPOSAL_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

export function proposalStatusTone(status: ProposalStatus): Tone {
  return PROPOSAL_STATUS_OPTIONS.find((option) => option.value === status)?.tone ?? "orange";
}

/**
 * !NOTE: 一覧のURL(`?status=`)はブラウザで直接書き換えられうるため、未知の値・未指定は
 *        既定(確認待ち)へ丸めて必ず描画できる状態を保つ。実際にAPIへ問い合わせたときの
 *        不正値422判定とは別の、画面表示側の防御。
 */
export function normalizeProposalStatus(value: string | null): ProposalStatus {
  return PROPOSAL_STATUS_OPTIONS.some((option) => option.value === value) ? (value as ProposalStatus) : "pending";
}

const PROPOSAL_MATERIAL_KIND_OPTIONS: { value: ProposalMaterialKind; label: string; tone: Tone }[] = [
  { value: "report", label: "日報", tone: "purple" },
  { value: "feedback", label: "講師フィードバック", tone: "green" },
  { value: "mood", label: "きもち", tone: "orange" },
  { value: "progress", label: "課題の進捗", tone: "blue" },
];

export function proposalMaterialKindLabel(kind: ProposalMaterialKind): string {
  return PROPOSAL_MATERIAL_KIND_OPTIONS.find((option) => option.value === kind)?.label ?? kind;
}

export function proposalMaterialKindTone(kind: ProposalMaterialKind): Tone {
  return PROPOSAL_MATERIAL_KIND_OPTIONS.find((option) => option.value === kind)?.tone ?? "purple";
}
