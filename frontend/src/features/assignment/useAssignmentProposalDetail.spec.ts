import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useAssignmentProposalDetail } from "./useAssignmentProposalDetail";
import { ApiError, apiClient } from "../../lib/apiClient";
import type { AssignmentDetail, ProposalDetail } from "../../lib/types";

vi.mock("../../lib/apiClient", () => {
  class MockApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  }
  return {
    apiClient: {
      get: vi.fn(),
      post: vi.fn(),
      del: vi.fn(),
    },
    ApiError: MockApiError,
  };
});

const mockedApiClient = vi.mocked(apiClient);

const detail: ProposalDetail = {
  id: 10,
  target: { id: 2, displayName: "ハルカ" },
  title: "タイトル",
  aim: "ねらい",
  status: "pending",
  createdAt: "2026-09-24T00:00:00Z",
  decidedAt: null,
  body: "課題文",
  messageForMember: "ひとこと",
  rationale: "理由",
  estimateMinutes: 20,
  materials: [],
  progress: { submittedCount: 1, reviewedCount: 1, notSubmittedCount: 0, recentMoods: [] },
  generator: "rule_based_v1",
  assignmentId: null,
  rejectReason: null,
  decidedBy: null,
  edited: false,
};

describe("useAssignmentProposalDetail", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("マウント時にapiClient.getが呼ばれ、proposalにセットされる", async () => {
    mockedApiClient.get.mockResolvedValue(detail);

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignment-proposals/10");
    expect(result.current.proposal).toEqual(detail);
    expect(result.current.notFound).toBe(false);
  });

  it("pending/rejectedの課題案では配信した課題(assignments)を取得しない(deliveredAssignmentはnullのまま)", async () => {
    mockedApiClient.get.mockResolvedValueOnce(detail);

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledTimes(1);
    expect(result.current.deliveredAssignment).toBeNull();
  });

  it("approvedかつassignmentIdがある課題案は、配信した課題(GET /api/assignments/{id})を取得しdeliveredAssignmentにセットする", async () => {
    const approved: ProposalDetail = { ...detail, status: "approved", assignmentId: 7 };
    const deliveredAssignmentStub: AssignmentDetail = {
      id: 7,
      title: "配信済み課題",
      body: "本文",
      status: "not_submitted",
      createdAt: "2026-09-25T00:00:00Z",
      submission: null,
      target: { id: 2, displayName: "ハルカ" },
      messageForMember: "ひとこと",
    };
    mockedApiClient.get.mockImplementation(async (path: string) => {
      if (path === "/api/assignment-proposals/10") return approved;
      if (path === "/api/assignments/7") return deliveredAssignmentStub;
      throw new Error(`unexpected path: ${path}`);
    });

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignments/7");
    expect(result.current.deliveredAssignment).toEqual(deliveredAssignmentStub);
  });

  it("配信した課題の取得に失敗した場合、deliveredAssignmentはnullのままになる", async () => {
    const approved: ProposalDetail = { ...detail, status: "approved", assignmentId: 7 };
    mockedApiClient.get.mockImplementation(async (path: string) => {
      if (path === "/api/assignment-proposals/10") return approved;
      throw new Error("not found");
    });

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    expect(result.current.deliveredAssignment).toBeNull();
  });

  it("取得失敗時、notFoundがtrueになる(講師以外の403・存在しないIDの404を区別しない)", async () => {
    mockedApiClient.get.mockRejectedValue(new Error("not found"));

    const { result } = renderHook(() => useAssignmentProposalDetail(999));
    await act(async () => {});

    expect(result.current.notFound).toBe(true);
  });

  it("approve成功時、apiClient.postが期待するペイロードで呼ばれproposalが更新され、noticeが成功になる", async () => {
    mockedApiClient.get.mockResolvedValue(detail);
    const approved: ProposalDetail = { ...detail, status: "approved", assignmentId: 5 };
    mockedApiClient.post.mockResolvedValue(approved);

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    let ok = false;
    await act(async () => {
      ok = await result.current.approve("新タイトル", "新課題文", "ひとこと2");
    });

    expect(ok).toBe(true);
    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/assignment-proposals/10/approve", {
      title: "新タイトル",
      body: "新課題文",
      messageForMember: "ひとこと2",
    });
    expect(result.current.proposal).toEqual(approved);
    expect(result.current.notice).toEqual({ severity: "success", message: "課題を配信しました。" });
  });

  it("approve失敗時、noticeがエラーになりfalseを返す", async () => {
    mockedApiClient.get.mockResolvedValue(detail);
    mockedApiClient.post.mockRejectedValue(new Error("conflict"));

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    let ok = true;
    await act(async () => {
      ok = await result.current.approve("t", "b", "");
    });

    expect(ok).toBe(false);
    expect(result.current.notice).toEqual({
      severity: "error",
      message: "配信できませんでした。時間をおいて再度お試しください。",
    });
  });

  it("approveが409で失敗した場合、既に決定済みである旨のnoticeになり課題案を再取得する", async () => {
    mockedApiClient.get.mockResolvedValueOnce(detail);
    mockedApiClient.post.mockRejectedValue(new ApiError(409, "conflict"));

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    const alreadyRejected: ProposalDetail = { ...detail, status: "rejected", rejectReason: "他の講師が見送り" };
    mockedApiClient.get.mockResolvedValueOnce(alreadyRejected);
    mockedApiClient.get.mockClear();

    let ok = true;
    await act(async () => {
      ok = await result.current.approve("t", "b", "");
    });

    expect(ok).toBe(false);
    expect(result.current.notice).toEqual({
      severity: "error",
      message: "既に決定済みのため配信できませんでした。最新の状態を再読み込みします。",
    });
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignment-proposals/10");
    expect(result.current.proposal).toEqual(alreadyRejected);
  });

  it("reject成功時、空(空白のみ含む)の理由はnullとして送られproposalが更新され、noticeが成功になる", async () => {
    mockedApiClient.get.mockResolvedValue(detail);
    const rejected: ProposalDetail = { ...detail, status: "rejected", rejectReason: null };
    mockedApiClient.post.mockResolvedValue(rejected);

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    let ok = false;
    await act(async () => {
      ok = await result.current.reject("   ");
    });

    expect(ok).toBe(true);
    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/assignment-proposals/10/reject", { reason: null });
    expect(result.current.proposal).toEqual(rejected);
    expect(result.current.notice).toEqual({ severity: "success", message: "課題案を見送りました。" });
  });

  it("reject成功時、理由を入力していればそのまま送られる", async () => {
    mockedApiClient.get.mockResolvedValue(detail);
    const rejected: ProposalDetail = { ...detail, status: "rejected", rejectReason: "理由" };
    mockedApiClient.post.mockResolvedValue(rejected);

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    await act(async () => {
      await result.current.reject("理由");
    });

    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/assignment-proposals/10/reject", { reason: "理由" });
  });

  it("reject失敗時、noticeがエラーになりfalseを返す", async () => {
    mockedApiClient.get.mockResolvedValue(detail);
    mockedApiClient.post.mockRejectedValue(new Error("conflict"));

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    let ok = true;
    await act(async () => {
      ok = await result.current.reject("");
    });

    expect(ok).toBe(false);
    expect(result.current.notice).toEqual({
      severity: "error",
      message: "見送りできませんでした。時間をおいて再度お試しください。",
    });
  });

  it("rejectが409で失敗した場合、既に決定済みである旨のnoticeになり課題案を再取得する", async () => {
    mockedApiClient.get.mockResolvedValueOnce(detail);
    mockedApiClient.post.mockRejectedValue(new ApiError(409, "conflict"));

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    // 再取得した課題案が「既に別の講師が配信した(approved)」状態を返すケース。
    // このケースでは配信済みの課題(assignments)も追加で取得されるため、そちらも用意しておく。
    const alreadyApproved: ProposalDetail = { ...detail, status: "approved", assignmentId: 7 };
    const deliveredAssignmentStub: AssignmentDetail = {
      id: 7,
      title: "配信済み課題",
      body: "本文",
      status: "not_submitted",
      createdAt: "2026-09-25T00:00:00Z",
      submission: null,
      target: { id: 2, displayName: "ハルカ" },
      messageForMember: "ひとこと",
    };
    mockedApiClient.get.mockResolvedValueOnce(alreadyApproved);
    mockedApiClient.get.mockResolvedValueOnce(deliveredAssignmentStub);
    mockedApiClient.get.mockClear();

    let ok = true;
    await act(async () => {
      ok = await result.current.reject("");
    });

    expect(ok).toBe(false);
    expect(result.current.notice).toEqual({
      severity: "error",
      message: "既に決定済みのため見送れませんでした。最新の状態を再読み込みします。",
    });
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignment-proposals/10");
    expect(result.current.proposal).toEqual(alreadyApproved);
  });

  it("notice表示後5秒経過すると自動的にnullに戻る", async () => {
    vi.useFakeTimers();
    mockedApiClient.get.mockResolvedValue(detail);
    mockedApiClient.post.mockResolvedValue({ ...detail, status: "approved" });

    const { result } = renderHook(() => useAssignmentProposalDetail(10));
    await act(async () => {});

    await act(async () => {
      await result.current.approve("t", "b", "");
    });
    expect(result.current.notice).not.toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(result.current.notice).toBeNull();
  });
});
