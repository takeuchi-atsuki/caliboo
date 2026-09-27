import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useAssignmentProposals } from "./useAssignmentProposals";
import { apiClient } from "../../lib/apiClient";
import type { ProposalDetail, ProposalListItem, ProposalMember, ProposalStatus } from "../../lib/types";

vi.mock("../../lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
  },
}));

const mockedApiClient = vi.mocked(apiClient);

const listItem: ProposalListItem = {
  id: 10,
  target: { id: 2, displayName: "ハルカ" },
  title: "レビュー指摘への返し方を練習しよう",
  aim: "指摘を前向きに受け止めて返す力",
  status: "pending",
  createdAt: "2026-09-24T00:00:00Z",
  decidedAt: null,
};

const members: ProposalMember[] = [{ id: 2, displayName: "ハルカ", hasPending: true }];

const detail: ProposalDetail = {
  ...listItem,
  body: "課題文",
  messageForMember: "ひとこと",
  rationale: "理由",
  estimateMinutes: 20,
  materials: [],
  progress: { submittedCount: 2, reviewedCount: 2, notSubmittedCount: 0, recentMoods: ["foggy"] },
  generator: "rule_based_v1",
  assignmentId: null,
  rejectReason: null,
  decidedBy: null,
  edited: false,
};

describe("useAssignmentProposals", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("enabled=trueのときマウント時にapiClient.getがstatus付きで呼ばれ、一覧・対象者・確認待ち件数がセットされる", async () => {
    mockedApiClient.get.mockResolvedValue({ proposals: [listItem], members, pendingCount: 1 });

    const { result } = renderHook(() => useAssignmentProposals("pending", true));
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignment-proposals?status=pending");
    expect(result.current.proposals).toEqual([listItem]);
    expect(result.current.members).toEqual(members);
    expect(result.current.pendingCount).toBe(1);
  });

  it("enabled=falseのときは取得しない(新入社員での不要な呼び出しを避ける)", async () => {
    const { result } = renderHook(() => useAssignmentProposals("pending", false));
    await act(async () => {});

    expect(mockedApiClient.get).not.toHaveBeenCalled();
    expect(result.current.proposals).toEqual([]);
    expect(result.current.pendingCount).toBe(0);
  });

  it("enabledがfalse→trueに変わると取得を開始する", async () => {
    mockedApiClient.get.mockResolvedValue({ proposals: [listItem], members, pendingCount: 1 });

    const { result, rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) => useAssignmentProposals("pending", enabled),
      { initialProps: { enabled: false } },
    );
    await act(async () => {});

    expect(mockedApiClient.get).not.toHaveBeenCalled();

    rerender({ enabled: true });
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignment-proposals?status=pending");
    expect(result.current.proposals).toEqual([listItem]);
  });

  it("初回取得(マウント時)が失敗した場合、noticeがエラーになる(未処理のPromise拒否にならない)", async () => {
    mockedApiClient.get.mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => useAssignmentProposals("pending", true));
    await act(async () => {});

    expect(result.current.notice).toEqual({
      severity: "error",
      message: "課題案の取得に失敗しました。時間をおいて再度お試しください。",
    });
    expect(result.current.proposals).toEqual([]);
  });

  it("statusが変わると、新しいstatusで再取得する", async () => {
    mockedApiClient.get.mockResolvedValue({ proposals: [], members: [], pendingCount: 0 });

    const { rerender } = renderHook(({ status }: { status: ProposalStatus }) => useAssignmentProposals(status, true), {
      initialProps: { status: "pending" },
    });
    await act(async () => {});
    mockedApiClient.get.mockClear();

    rerender({ status: "approved" });
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignment-proposals?status=approved");
  });

  it("generateProposal成功時、apiClient.postが期待するペイロードで呼ばれ、一覧が再取得され、作成された課題案を返す", async () => {
    mockedApiClient.get.mockResolvedValue({ proposals: [listItem], members, pendingCount: 1 });
    mockedApiClient.post.mockResolvedValue(detail);

    const { result } = renderHook(() => useAssignmentProposals("pending", true));
    await act(async () => {});
    mockedApiClient.get.mockClear();

    let created: ProposalDetail | null = null;
    await act(async () => {
      created = await result.current.generateProposal(2);
    });

    expect(created).toEqual(detail);
    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/assignment-proposals", { userId: 2 });
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignment-proposals?status=pending");
  });

  it("generateProposal実行中はgeneratingがtrueになり、完了後にfalseへ戻る", async () => {
    mockedApiClient.get.mockResolvedValue({ proposals: [], members: [], pendingCount: 0 });
    let resolvePost: (value: ProposalDetail) => void = () => {};
    mockedApiClient.post.mockImplementation(
      () =>
        new Promise<ProposalDetail>((resolve) => {
          resolvePost = resolve;
        }),
    );

    const { result } = renderHook(() => useAssignmentProposals("pending", true));
    await act(async () => {});

    expect(result.current.generating).toBe(false);

    let generatePromise!: Promise<ProposalDetail | null>;
    act(() => {
      generatePromise = result.current.generateProposal(2);
    });

    expect(result.current.generating).toBe(true);

    await act(async () => {
      resolvePost(detail);
      await generatePromise;
    });

    expect(result.current.generating).toBe(false);
  });

  it("generateProposal失敗時、noticeがエラーになりnullを返す", async () => {
    mockedApiClient.get.mockResolvedValue({ proposals: [], members: [], pendingCount: 0 });
    mockedApiClient.post.mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => useAssignmentProposals("pending", true));
    await act(async () => {});

    let created: ProposalDetail | null = detail;
    await act(async () => {
      created = await result.current.generateProposal(2);
    });

    expect(created).toBeNull();
    expect(result.current.notice).toEqual({
      severity: "error",
      message: "課題案の作成に失敗しました。時間をおいて再度お試しください。",
    });
  });

  it("notice表示後5秒経過すると自動的にnullに戻る", async () => {
    vi.useFakeTimers();
    mockedApiClient.get.mockResolvedValue({ proposals: [], members: [], pendingCount: 0 });
    mockedApiClient.post.mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => useAssignmentProposals("pending", true));
    await act(async () => {});

    await act(async () => {
      await result.current.generateProposal(2);
    });
    expect(result.current.notice).not.toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(result.current.notice).toBeNull();
  });
});
