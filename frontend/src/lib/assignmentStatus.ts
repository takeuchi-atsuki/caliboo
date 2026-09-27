import type { AssignmentStatus, Tone } from "./types";

export const ASSIGNMENT_STATUS_OPTIONS: { value: AssignmentStatus; label: string; tone: Tone }[] = [
  { value: "not_submitted", label: "未提出", tone: "orange" },
  { value: "submitted", label: "レビュー待ち", tone: "blue" },
  { value: "reviewed", label: "フィードバック済み", tone: "green" },
];

export function assignmentStatusLabel(status: AssignmentStatus): string {
  return ASSIGNMENT_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

export function assignmentStatusTone(status: AssignmentStatus): Tone {
  return ASSIGNMENT_STATUS_OPTIONS.find((option) => option.value === status)?.tone ?? "green";
}
