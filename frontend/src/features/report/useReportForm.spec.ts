import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useReportForm } from "./useReportForm";
import { apiClient } from "../../lib/apiClient";
import type { ReportDraftItem, ReportHistoryItem } from "../../lib/types";

vi.mock("../../lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
  },
}));

const mockedApiClient = vi.mocked(apiClient);

const TODAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const USER_ID = 1;
const OTHER_USER_ID = 2;

const historyItem: ReportHistoryItem = {
  date: "2026-09-10",
  keep: "keep-history",
  problem: "problem-history",
  try: "try-history",
  mood: ["happy"],
  moodComment: "history-comment",
};

const draftItem: ReportDraftItem = {
  id: 1,
  date: "2026-09-01",
  savedAt: "2026-09-01T10:00:00Z",
  keep: "keep-draft",
  problem: "problem-draft",
  try: "try-draft",
  mood: ["tired"],
  moodComment: "draft-comment",
};

function setupApiMocks() {
  mockedApiClient.get.mockImplementation(async (path: string) => {
    if (path === "/api/report/history") {
      return { history: [historyItem] };
    }
    if (path === "/api/report/drafts") {
      return { drafts: [draftItem] };
    }
    throw new Error(`unexpected path: ${path}`);
  });
  mockedApiClient.post.mockResolvedValue({ id: "rpt_20260911_1", status: "submitted", savedAt: "2026-09-11T00:00:00Z" });
  mockedApiClient.del.mockResolvedValue(undefined);
}

describe("useReportForm", () => {
  beforeEach(() => {
    window.localStorage.clear();
    setupApiMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("マウント時にapiClient.getが/api/report/historyで呼ばれ、historyにセットされる", async () => {
    const { result } = renderHook(() => useReportForm(USER_ID));

    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/report/history");
    expect(mockedApiClient.get).not.toHaveBeenCalledWith("/api/report/drafts");
    expect(result.current.history).toEqual([historyItem]);
  });

  it("fetchDraftsを呼ぶと、apiClient.getが/api/report/draftsで呼ばれ、draftsにセットされる", async () => {
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    mockedApiClient.get.mockClear();

    await act(async () => {
      await result.current.fetchDrafts();
    });

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/report/drafts");
    expect(result.current.drafts).toEqual([draftItem]);
  });

  it("submit('draft')成功時、apiClient.postが期待するペイロードで呼ばれ、feedbackが下書き保存成功になり、drafts再取得される", async () => {
    mockedApiClient.post.mockResolvedValueOnce({ id: "rpt_x", status: "draft", savedAt: "2026-09-11T00:00:00Z" });
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    act(() => {
      result.current.setKeep("keep-value");
      result.current.setProblem("problem-value");
      result.current.setTryText("try-value");
      result.current.setMood(["happy"]);
      result.current.setMoodComment("comment-value");
    });

    mockedApiClient.get.mockClear();

    await act(async () => {
      await result.current.submit("draft");
    });

    expect(mockedApiClient.post).toHaveBeenCalledTimes(1);
    const [path, payload] = mockedApiClient.post.mock.calls[0];
    expect(path).toBe("/api/report");
    expect(payload).toMatchObject({
      keep: "keep-value",
      problem: "problem-value",
      try: "try-value",
      mood: ["happy"],
      moodComment: "comment-value",
      status: "draft",
    });
    expect((payload as { date: string }).date).toMatch(TODAY_PATTERN);

    expect(result.current.feedback).toEqual({ severity: "success", message: "下書きを保存しました。" });
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/report/drafts");
    expect(mockedApiClient.get).not.toHaveBeenCalledWith("/api/report/history");
  });

  it("submit('submitted')成功時、feedbackが提出成功メッセージになり、historyが再取得され、draftDateがnullにリセットされる", async () => {
    mockedApiClient.post.mockResolvedValueOnce({ id: "rpt_20260911_1", status: "submitted", savedAt: "2026-09-11T00:00:00Z" });
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    act(() => {
      result.current.loadDraft(draftItem);
    });

    mockedApiClient.get.mockClear();

    await act(async () => {
      await result.current.submit("submitted");
    });

    expect(result.current.feedback).toEqual({ severity: "success", message: "提出しました！（rpt_20260911_1）" });
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/report/history");
    expect(result.current.draftDate).toBeNull();
  });

  it("submit('draft')失敗時、feedbackが下書き保存失敗メッセージになる", async () => {
    mockedApiClient.post.mockRejectedValueOnce(new Error("network error"));
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    await act(async () => {
      await result.current.submit("draft");
    });

    expect(result.current.feedback).toEqual({
      severity: "error",
      message: "下書きの保存に失敗しました。時間をおいて再度お試しください。",
    });
  });

  it("submit('submitted')失敗時、feedbackが提出失敗メッセージになる", async () => {
    mockedApiClient.post.mockRejectedValueOnce(new Error("network error"));
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    await act(async () => {
      await result.current.submit("submitted");
    });

    expect(result.current.feedback).toEqual({
      severity: "error",
      message: "提出に失敗しました。時間をおいて再度お試しください。",
    });
  });

  it("loadDraft後にsubmitすると、送信ペイロードのdateがtoday()ではなくdraftDate(item.date)になる", async () => {
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    act(() => {
      result.current.loadDraft(draftItem);
    });

    expect(result.current.draftDate).toBe(draftItem.date);

    await act(async () => {
      await result.current.submit("draft");
    });

    const [, payload] = mockedApiClient.post.mock.calls[0];
    expect((payload as { date: string }).date).toBe(draftItem.date);
  });

  it("deleteDraft成功時、draftsから該当idが除去される", async () => {
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    await act(async () => {
      await result.current.fetchDrafts();
    });
    expect(result.current.drafts).toEqual([draftItem]);

    await act(async () => {
      await result.current.deleteDraft(draftItem.id);
    });

    expect(mockedApiClient.del).toHaveBeenCalledWith(`/api/report/drafts/${draftItem.id}`);
    expect(result.current.drafts).toEqual([]);
  });

  it("feedback表示中にloadDraftを呼ぶと、feedbackが消去される", async () => {
    mockedApiClient.post.mockResolvedValueOnce({ id: "rpt_x", status: "draft", savedAt: "2026-09-11T00:00:00Z" });
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    await act(async () => {
      await result.current.submit("draft");
    });
    expect(result.current.feedback).not.toBeNull();

    act(() => {
      result.current.loadDraft(draftItem);
    });

    expect(result.current.feedback).toBeNull();
  });

  it("feedback表示中にclearDraftを呼ぶと、feedbackが消去される", async () => {
    mockedApiClient.post.mockResolvedValueOnce({ id: "rpt_x", status: "draft", savedAt: "2026-09-11T00:00:00Z" });
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    await act(async () => {
      await result.current.submit("draft");
    });
    expect(result.current.feedback).not.toBeNull();

    act(() => {
      result.current.clearDraft();
    });

    expect(result.current.feedback).toBeNull();
  });

  it("clearDraftを呼ぶと、フォーム状態・draftDate・feedbackが初期化される", async () => {
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    act(() => {
      result.current.loadDraft(draftItem);
    });
    expect(result.current.keep).toBe(draftItem.keep);
    expect(result.current.draftDate).toBe(draftItem.date);

    act(() => {
      result.current.clearDraft();
    });

    expect(result.current.keep).toBe("");
    expect(result.current.problem).toBe("");
    expect(result.current.tryText).toBe("");
    expect(result.current.mood).toEqual([]);
    expect(result.current.moodComment).toBe("");
    expect(result.current.draftDate).toBeNull();
    expect(result.current.feedback).toBeNull();
  });

  it("deleteDraft失敗時、feedbackが下書き削除失敗メッセージになる", async () => {
    mockedApiClient.del.mockRejectedValueOnce(new Error("network error"));
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    await act(async () => {
      await result.current.deleteDraft(999);
    });

    expect(result.current.feedback).toEqual({
      severity: "error",
      message: "下書きの削除に失敗しました。時間をおいて再度お試しください。",
    });
  });

  it("feedbackセット後5秒経過すると自動的にnullに戻る", async () => {
    vi.useFakeTimers();
    mockedApiClient.post.mockResolvedValueOnce({ id: "rpt_x", status: "draft", savedAt: "2026-09-11T00:00:00Z" });
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    await act(async () => {
      await result.current.submit("draft");
    });

    expect(result.current.feedback).not.toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(result.current.feedback).toBeNull();
  });

  it("feedback表示中に別のメッセージへ更新された場合、その更新時点から改めて5秒後に消える", async () => {
    vi.useFakeTimers();
    mockedApiClient.post
      .mockResolvedValueOnce({ id: "rpt_x", status: "draft", savedAt: "2026-09-11T00:00:00Z" })
      .mockRejectedValueOnce(new Error("network error"));
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    await act(async () => {
      await result.current.submit("draft");
    });
    expect(result.current.feedback).toEqual({ severity: "success", message: "下書きを保存しました。" });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(result.current.feedback).not.toBeNull();

    await act(async () => {
      await result.current.submit("draft");
    });
    expect(result.current.feedback).toEqual({
      severity: "error",
      message: "下書きの保存に失敗しました。時間をおいて再度お試しください。",
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(result.current.feedback).not.toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(result.current.feedback).toBeNull();
  });
});

describe("useReportForm 入力内容の自動保存・復元", () => {
  // 画面の再読み込みは、フックをアンマウントして新たにマウントし直すことで再現する
  const remount = async (unmount: () => void, userId: number = USER_ID) => {
    unmount();
    const rendered = renderHook(() => useReportForm(userId));
    await act(async () => {});
    return rendered;
  };

  beforeEach(() => {
    window.localStorage.clear();
    setupApiMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("入力後に再読み込みすると、フォームは空のままpendingRestoreに前回の入力内容と保存日時が入る", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-value");
      first.result.current.setProblem("problem-value");
      first.result.current.setTryText("try-value");
      first.result.current.setMood(["fun"]);
      first.result.current.setMoodComment("comment-value");
    });

    const { result } = await remount(first.unmount);

    expect(result.current.keep).toBe("");
    expect(result.current.problem).toBe("");
    expect(result.current.tryText).toBe("");
    expect(result.current.mood).toEqual([]);
    expect(result.current.moodComment).toBe("");
    expect(result.current.draftDate).toBeNull();
    expect(result.current.pendingRestore).toMatchObject({
      keep: "keep-value",
      problem: "problem-value",
      try: "try-value",
      mood: ["fun"],
      moodComment: "comment-value",
      draftDate: null,
    });
    expect(Number.isNaN(Date.parse(result.current.pendingRestore!.savedAt))).toBe(false);
  });

  it("restoreAutosaveを呼ぶと、前回の入力内容と編集中の下書き日付がフォームに戻り、pendingRestoreがnullになる", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.loadDraft(draftItem);
    });
    act(() => {
      first.result.current.setKeep("keep-edited");
    });

    const { result } = await remount(first.unmount);
    expect(result.current.draftDate).toBeNull();

    act(() => {
      result.current.restoreAutosave();
    });

    expect(result.current.pendingRestore).toBeNull();
    expect(result.current.keep).toBe("keep-edited");
    expect(result.current.problem).toBe(draftItem.problem);
    expect(result.current.tryText).toBe(draftItem.try);
    expect(result.current.mood).toEqual(draftItem.mood);
    expect(result.current.moodComment).toBe(draftItem.moodComment);
    expect(result.current.draftDate).toBe(draftItem.date);
  });

  it("feedback表示中にrestoreAutosaveを呼ぶと、feedbackが消去される", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-value");
    });

    const { result } = await remount(first.unmount);
    await act(async () => {
      await result.current.submit("draft");
    });
    expect(result.current.feedback).not.toBeNull();

    act(() => {
      result.current.restoreAutosave();
    });
    expect(result.current.feedback).toBeNull();
  });

  it("discardAutosaveを呼ぶとpendingRestoreがnullになり、再度再読み込みしても復元候補は出ない", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-value");
    });

    const second = await remount(first.unmount);
    act(() => {
      second.result.current.discardAutosave();
    });
    expect(second.result.current.pendingRestore).toBeNull();
    expect(second.result.current.keep).toBe("");

    const { result } = await remount(second.unmount);
    expect(result.current.pendingRestore).toBeNull();
  });

  it("submit('submitted')成功後に再読み込みしても復元候補は出ない", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-value");
    });
    await act(async () => {
      await first.result.current.submit("submitted");
    });

    const { result } = await remount(first.unmount);
    expect(result.current.pendingRestore).toBeNull();
  });

  it("clearDraft後に再読み込みしても復元候補は出ない", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.loadDraft(draftItem);
    });
    act(() => {
      first.result.current.clearDraft();
    });

    const { result } = await remount(first.unmount);
    expect(result.current.pendingRestore).toBeNull();
  });

  it("submit('draft')成功後に再読み込みすると復元候補が出る", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-value");
    });
    await act(async () => {
      await first.result.current.submit("draft");
    });

    const { result } = await remount(first.unmount);
    expect(result.current.pendingRestore).toMatchObject({ keep: "keep-value" });
  });

  it("別ユーザーIDでマウントすると、前ユーザーの自動保存は復元候補として出ない(セッション切れ後の別ユーザーログイン対策)", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-value");
    });

    const { result } = await remount(first.unmount, OTHER_USER_ID);
    expect(result.current.pendingRestore).toBeNull();
  });

  it("何も入力せずに再読み込みした場合は復元候補が出ない", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});

    const { result } = await remount(first.unmount);
    expect(result.current.pendingRestore).toBeNull();
  });

  it("入力内容を全て空に戻してから再読み込みした場合は復元候補が出ない", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-value");
    });
    act(() => {
      first.result.current.setKeep("");
    });

    const { result } = await remount(first.unmount);
    expect(result.current.pendingRestore).toBeNull();
  });

  it("復元候補が出ている間に入力・提出・clearDraftをして再読み込みしても、前回の入力内容が復元候補として残る", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-previous");
    });

    const second = await remount(first.unmount);
    act(() => {
      second.result.current.setKeep("keep-new");
    });
    await act(async () => {
      await second.result.current.submit("submitted");
    });
    act(() => {
      second.result.current.clearDraft();
    });

    const { result } = await remount(second.unmount);
    expect(result.current.pendingRestore).toMatchObject({ keep: "keep-previous" });
  });

  it("復元候補を破棄した後に入力した内容は、再び自動保存される", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-previous");
    });

    const second = await remount(first.unmount);
    act(() => {
      second.result.current.setKeep("keep-new");
    });
    act(() => {
      second.result.current.discardAutosave();
    });
    expect(second.result.current.keep).toBe("keep-new");

    const { result } = await remount(second.unmount);
    expect(result.current.pendingRestore).toMatchObject({ keep: "keep-new" });
  });

  it("下書き一覧から下書きを選択しただけで再読み込みしても、その下書きが復元候補として出る", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.loadDraft(draftItem);
    });

    const { result } = await remount(first.unmount);
    expect(result.current.pendingRestore).toMatchObject({ keep: draftItem.keep, draftDate: draftItem.date });
  });

  it("復元候補が出ている間に入力した内容は、restoreAutosaveで前回の入力内容に置き換わる", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-previous");
    });

    const { result } = await remount(first.unmount);
    act(() => {
      result.current.setKeep("keep-new");
      result.current.setProblem("problem-new");
    });
    act(() => {
      result.current.restoreAutosave();
    });

    expect(result.current.keep).toBe("keep-previous");
    expect(result.current.problem).toBe("");
  });

  it("下書き未選択の入力内容を翌日に復元して提出すると、送信ペイロードのdateは書き始めた日ではなく提出した日になる", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-09-24T12:00:00Z"));
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-value");
    });

    vi.setSystemTime(new Date("2026-09-25T12:00:00Z"));
    const { result } = await remount(first.unmount);
    act(() => {
      result.current.restoreAutosave();
    });
    await act(async () => {
      await result.current.submit("submitted");
    });

    const [, payload] = mockedApiClient.post.mock.calls[0];
    expect(payload).toMatchObject({ keep: "keep-value", date: "2026-09-25" });
  });

  it("submit('submitted')成功後に編集を続けると、フォームの内容全体が再び自動保存される", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-value");
    });
    await act(async () => {
      await first.result.current.submit("submitted");
    });
    act(() => {
      first.result.current.setProblem("problem-added");
    });

    const { result } = await remount(first.unmount);
    expect(result.current.pendingRestore).toMatchObject({ keep: "keep-value", problem: "problem-added" });
  });

  it("restoreAutosaveで復元した後に編集した内容は、再び自動保存される", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-previous");
    });

    const second = await remount(first.unmount);
    act(() => {
      second.result.current.restoreAutosave();
    });
    act(() => {
      second.result.current.setProblem("problem-added");
    });

    const { result } = await remount(second.unmount);
    expect(result.current.pendingRestore).toMatchObject({ keep: "keep-previous", problem: "problem-added" });
  });

  it("復元候補が出ている間に入力だけして再読み込みしても、前回の入力内容が復元候補として残る", async () => {
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-previous");
    });

    const second = await remount(first.unmount);
    act(() => {
      second.result.current.setKeep("keep-new");
    });

    const { result } = await remount(second.unmount);
    expect(result.current.pendingRestore).toMatchObject({ keep: "keep-previous" });
  });

  it("送信中に入力した内容も、submit('submitted')成功時に消去され再読み込みしても復元候補は出ない", async () => {
    let resolvePost: (value: unknown) => void = () => {};
    mockedApiClient.post.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolvePost = resolve;
        }),
    );
    const first = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    act(() => {
      first.result.current.setKeep("keep-value");
    });

    let submitting: Promise<unknown> = Promise.resolve();
    act(() => {
      submitting = first.result.current.submit("submitted");
    });
    act(() => {
      first.result.current.setProblem("typed-while-sending");
    });
    await act(async () => {
      resolvePost({ id: "rpt_20260925_1", status: "submitted", savedAt: "2026-09-25T00:00:00Z" });
      await submitting;
    });

    const { result } = await remount(first.unmount);
    expect(result.current.pendingRestore).toBeNull();
  });

  it("localStorageが例外を投げる環境でも、入力・提出が通常どおり行える", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const { result } = renderHook(() => useReportForm(USER_ID));
    await act(async () => {});
    expect(result.current.pendingRestore).toBeNull();

    act(() => {
      result.current.setKeep("keep-value");
    });
    await act(async () => {
      await result.current.submit("submitted");
    });

    expect(result.current.keep).toBe("keep-value");
    expect(result.current.feedback).toEqual({ severity: "success", message: "提出しました！（rpt_20260911_1）" });
  });
});
