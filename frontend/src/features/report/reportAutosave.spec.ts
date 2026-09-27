import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { clearAutosave, readAutosave, writeAutosave, type ReportAutosaveContent } from "./reportAutosave";

const STORAGE_KEY = "caliboo:report-autosave";

const content: ReportAutosaveContent = {
  keep: "keep-value",
  problem: "",
  try: "",
  mood: ["happy"],
  moodComment: "",
  draftDate: null,
};

const USER_ID = 1;
const OTHER_USER_ID = 2;

describe("reportAutosave", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("writeAutosaveで保存した内容をreadAutosaveで保存日時・保存者id付きで読み出せる", () => {
    writeAutosave(content, USER_ID);

    const saved = readAutosave(USER_ID);
    expect(saved).toMatchObject({ ...content, userId: USER_ID });
    expect(Number.isNaN(Date.parse(saved!.savedAt))).toBe(false);
  });

  it("空の入力内容をwriteAutosaveすると保存済みの内容が消える", () => {
    writeAutosave(content, USER_ID);
    writeAutosave({ ...content, keep: "", mood: [] }, USER_ID);

    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("本文が空でもdraftDateがあれば復元候補として読み出せる", () => {
    writeAutosave({ ...content, keep: "", mood: [], draftDate: "2026-09-01" }, USER_ID);

    expect(readAutosave(USER_ID)).toMatchObject({ draftDate: "2026-09-01" });
  });

  it("形式は正しいが全項目が空の保存値は、readAutosaveでnullになる", () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ ...content, keep: "", mood: [], savedAt: "2026-09-01T00:00:00Z", userId: USER_ID }),
    );

    expect(readAutosave(USER_ID)).toBeNull();
  });

  it("clearAutosaveで保存済みの内容が消える", () => {
    writeAutosave(content, USER_ID);
    clearAutosave();

    expect(readAutosave(USER_ID)).toBeNull();
  });

  it("保存者と異なるユーザーIDでreadAutosaveすると、復元候補は出ずに保存値が消去される(別ユーザーのログイン対策)", () => {
    writeAutosave(content, USER_ID);

    expect(readAutosave(OTHER_USER_ID)).toBeNull();
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it.each([
    ["JSONとして不正", "{not json"],
    ["オブジェクトでない", '"text"'],
    ["必須項目が欠けている", JSON.stringify({ keep: "a" })],
    ["savedAtが欠けている", JSON.stringify({ ...content, userId: USER_ID })],
    ["userIdが欠けている", JSON.stringify({ ...content, savedAt: "2026-09-01T00:00:00Z" })],
    ["userIdの型が不正", JSON.stringify({ ...content, savedAt: "2026-09-01T00:00:00Z", userId: "1" })],
    [
      "moodが配列でない",
      JSON.stringify({ ...content, mood: "happy", savedAt: "2026-09-01T00:00:00Z", userId: USER_ID }),
    ],
    [
      "moodに未知の値を含む",
      JSON.stringify({ ...content, mood: ["angry"], savedAt: "2026-09-01T00:00:00Z", userId: USER_ID }),
    ],
    ["savedAtが日時として解釈できない", JSON.stringify({ ...content, savedAt: "not-a-date", userId: USER_ID })],
    [
      "draftDateが日付形式でない",
      JSON.stringify({ ...content, draftDate: "", savedAt: "2026-09-01T00:00:00Z", userId: USER_ID }),
    ],
    [
      "draftDateの型が不正",
      JSON.stringify({ ...content, draftDate: 1, savedAt: "2026-09-01T00:00:00Z", userId: USER_ID }),
    ],
  ])("保存値が%sの場合、readAutosaveはnullを返す", (_, raw) => {
    window.localStorage.setItem(STORAGE_KEY, raw);

    expect(readAutosave(USER_ID)).toBeNull();
  });

  it("localStorageへのアクセスが例外を投げても、各関数は例外を外へ出さない", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    expect(readAutosave(USER_ID)).toBeNull();
    expect(() => writeAutosave(content, USER_ID)).not.toThrow();
    expect(() => writeAutosave({ ...content, keep: "", mood: [] }, USER_ID)).not.toThrow();
    expect(() => clearAutosave()).not.toThrow();
  });
});
