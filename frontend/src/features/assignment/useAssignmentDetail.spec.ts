import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useAssignmentDetail } from "./useAssignmentDetail";
import { apiClient } from "../../lib/apiClient";
import type { AssignmentDetail, MemberSubmission } from "../../lib/types";

vi.mock("../../lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
  },
}));

const mockedApiClient = vi.mocked(apiClient);

const detail: AssignmentDetail = {
  id: 1,
  title: "課題タイトル",
  body: "課題文",
  status: "not_submitted",
  createdAt: "2026-09-01T00:00:00Z",
  submission: null,
  target: null,
  messageForMember: null,
};

const submissions: MemberSubmission[] = [
  {
    user: { id: 2, displayName: "ソラ" },
    status: "not_submitted",
    submission: null,
  },
  {
    user: { id: 1, displayName: "ユウキ" },
    status: "submitted",
    submission: { answerText: "回答", submittedAt: "2026-09-02T00:00:00Z" },
  },
];

describe("useAssignmentDetail(member)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("マウント時にapiClient.getが/api/assignments/{id}のみで呼ばれ、assignmentにセットされる(submissionsは取得しない)", async () => {
    mockedApiClient.get.mockResolvedValue(detail);

    const { result } = renderHook(() => useAssignmentDetail(1, "member"));
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignments/1");
    expect(mockedApiClient.get).not.toHaveBeenCalledWith("/api/assignments/1/submissions");
    expect(result.current.assignment).toEqual(detail);
    expect(result.current.notFound).toBe(false);
    expect(result.current.submissions).toEqual([]);
  });

  it("取得失敗時、notFoundがtrueになる", async () => {
    mockedApiClient.get.mockRejectedValue(new Error("not found"));

    const { result } = renderHook(() => useAssignmentDetail(999, "member"));
    await act(async () => {});

    expect(result.current.notFound).toBe(true);
  });

  it("submitAnswer成功時、apiClient.postが呼ばれassignmentが更新され、noticeが成功になる", async () => {
    mockedApiClient.get.mockResolvedValue(detail);
    const submitted: AssignmentDetail = {
      ...detail,
      status: "submitted",
      submission: { answerText: "回答", submittedAt: "2026-09-02T00:00:00Z" },
    };
    mockedApiClient.post.mockResolvedValue(submitted);

    const { result } = renderHook(() => useAssignmentDetail(1, "member"));
    await act(async () => {});

    await act(async () => {
      await result.current.submitAnswer("回答");
    });

    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/assignments/1/submission", {
      answerText: "回答",
    });
    expect(result.current.assignment).toEqual(submitted);
    expect(result.current.notice).toEqual({ severity: "success", message: "回答を提出しました。" });
  });

  it("submitAnswer失敗時、noticeがエラーになり詳細が再取得される", async () => {
    mockedApiClient.get.mockResolvedValue(detail);
    mockedApiClient.post.mockRejectedValue(new Error("conflict"));

    const { result } = renderHook(() => useAssignmentDetail(1, "member"));
    await act(async () => {});

    mockedApiClient.get.mockClear();

    await act(async () => {
      await result.current.submitAnswer("回答");
    });

    expect(result.current.notice).toEqual({
      severity: "error",
      message: "保存できませんでした。最新の状態を再読み込みします。",
    });
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignments/1");
  });

  it("notice表示後5秒経過すると自動的にnullに戻る", async () => {
    vi.useFakeTimers();
    mockedApiClient.get.mockResolvedValue(detail);
    mockedApiClient.post.mockResolvedValue({ ...detail, status: "submitted" });

    const { result } = renderHook(() => useAssignmentDetail(1, "member"));
    await act(async () => {});

    await act(async () => {
      await result.current.submitAnswer("回答");
    });
    expect(result.current.notice).not.toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(result.current.notice).toBeNull();
  });
});

describe("useAssignmentDetail(admin)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("マウント時にapiClient.getが詳細・提出一覧の両方で呼ばれ、submissionsにセットされる", async () => {
    mockedApiClient.get.mockImplementation(async (path: string) => {
      if (path === "/api/assignments/1") return detail;
      if (path === "/api/assignments/1/submissions") return { submissions };
      throw new Error(`unexpected path: ${path}`);
    });

    const { result } = renderHook(() => useAssignmentDetail(1, "admin"));
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignments/1");
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignments/1/submissions");
    expect(result.current.submissions).toEqual(submissions);
  });

  it("submitFeedback成功時、対象userIdのsubmissionsの要素だけがレスポンスで置換される", async () => {
    mockedApiClient.get.mockImplementation(async (path: string) => {
      if (path === "/api/assignments/1") return detail;
      if (path === "/api/assignments/1/submissions") return { submissions };
      throw new Error(`unexpected path: ${path}`);
    });
    const reviewed: MemberSubmission = {
      user: { id: 1, displayName: "ユウキ" },
      status: "reviewed",
      submission: {
        answerText: "回答",
        submittedAt: "2026-09-02T00:00:00Z",
        feedbackComment: "コメント",
        feedbackAt: "2026-09-03T00:00:00Z",
      },
    };
    mockedApiClient.post.mockResolvedValue(reviewed);

    const { result } = renderHook(() => useAssignmentDetail(1, "admin"));
    await act(async () => {});

    await act(async () => {
      await result.current.submitFeedback(1, "コメント");
    });

    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/assignments/1/submissions/1/feedback", {
      comment: "コメント",
    });
    expect(result.current.submissions).toEqual([submissions[0], reviewed]);
    expect(result.current.notice).toEqual({
      severity: "success",
      message: "フィードバックを保存しました。",
    });
  });

  it("存在しない課題IDの場合、詳細・提出一覧の両方が失敗してもnotFoundになりsubmissionsは空のまま(未処理のPromise拒否にならない)", async () => {
    mockedApiClient.get.mockRejectedValue(new Error("not found"));

    const { result } = renderHook(() => useAssignmentDetail(999, "admin"));
    await act(async () => {});

    expect(result.current.notFound).toBe(true);
    expect(result.current.submissions).toEqual([]);
  });

  it("submitFeedback失敗時、noticeがエラーになり提出一覧が再取得される", async () => {
    mockedApiClient.get.mockImplementation(async (path: string) => {
      if (path === "/api/assignments/1") return detail;
      if (path === "/api/assignments/1/submissions") return { submissions };
      throw new Error(`unexpected path: ${path}`);
    });
    mockedApiClient.post.mockRejectedValue(new Error("conflict"));

    const { result } = renderHook(() => useAssignmentDetail(1, "admin"));
    await act(async () => {});

    mockedApiClient.get.mockClear();
    mockedApiClient.get.mockImplementation(async (path: string) => {
      if (path === "/api/assignments/1/submissions") return { submissions };
      throw new Error(`unexpected path: ${path}`);
    });

    await act(async () => {
      await result.current.submitFeedback(1, "コメント");
    });

    expect(result.current.notice).toEqual({
      severity: "error",
      message: "保存できませんでした。最新の状態を再読み込みします。",
    });
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignments/1/submissions");
  });
});
