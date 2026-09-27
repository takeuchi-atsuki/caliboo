import type { Mood } from "../../lib/types";

const STORAGE_KEY = "caliboo:report-autosave";

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const MOOD_VALUES: readonly Mood[] = ["happy", "fun", "foggy", "tired"];

export interface ReportAutosaveContent {
  keep: string;
  problem: string;
  try: string;
  mood: Mood[];
  moodComment: string;
  draftDate: string | null;
}

export interface ReportAutosave extends ReportAutosaveContent {
  savedAt: string;
  userId: number;
}

function hasContent(content: ReportAutosaveContent): boolean {
  return (
    content.keep !== "" ||
    content.problem !== "" ||
    content.try !== "" ||
    content.mood.length > 0 ||
    content.moodComment !== "" ||
    content.draftDate !== null
  );
}

function parseAutosave(raw: string): ReportAutosave | null {
  const value: unknown = JSON.parse(raw);
  if (typeof value !== "object" || value === null) return null;
  const v = value as Record<string, unknown>;
  const isString = (x: unknown): x is string => typeof x === "string";
  if (
    !isString(v.keep) ||
    !isString(v.problem) ||
    !isString(v.try) ||
    !isString(v.moodComment) ||
    !isString(v.savedAt) ||
    Number.isNaN(Date.parse(v.savedAt)) ||
    typeof v.userId !== "number" ||
    !(v.draftDate === null || (isString(v.draftDate) && DATE_PATTERN.test(v.draftDate))) ||
    !Array.isArray(v.mood) ||
    !v.mood.every((m) => MOOD_VALUES.includes(m as Mood))
  ) {
    return null;
  }
  return {
    keep: v.keep,
    problem: v.problem,
    try: v.try,
    mood: v.mood as Mood[],
    moodComment: v.moodComment,
    draftDate: v.draftDate,
    savedAt: v.savedAt,
    userId: v.userId,
  };
}

// localStorageはプライベートモードやサイトデータのブロックで例外を投げうるため、
// 読み書きの失敗はすべて「自動保存なし」として扱い、日報の入力・送信自体は妨げない。
//
// !NOTE: 保存エントリに保存者のuserIdを持たせ、現在ログイン中のユーザーと一致しない場合は
//        破棄する(復元候補として出さない)。セッション切れ後に別ユーザーが同じブラウザで
//        ログインすると、前ユーザーの書きかけの日報が復元候補に出てしまうため
//        (docs/screens/report.md・docs/screens/login.md参照)。
export function readAutosave(userId: number): ReportAutosave | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === null) return null;
    const parsed = parseAutosave(raw);
    if (!parsed) return null;
    if (parsed.userId !== userId) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return hasContent(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function writeAutosave(content: ReportAutosaveContent, userId: number): void {
  try {
    if (!hasContent(content)) {
      window.localStorage.removeItem(STORAGE_KEY);
      return;
    }
    const entry: ReportAutosave = { ...content, savedAt: new Date().toISOString(), userId };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entry));
  } catch {
    // 保存できない環境では自動保存しない
  }
}

export function clearAutosave(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // 消去できない環境では何もしない
  }
}
