import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useAssignmentList } from "./useAssignmentList";
import { apiClient } from "../../lib/apiClient";
import type { AssignmentListItem } from "../../lib/types";

vi.mock("../../lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
  },
}));

const mockedApiClient = vi.mocked(apiClient);

const listItem: AssignmentListItem = {
  id: 1,
  title: "課題タイトル",
  status: "not_submitted",
  createdAt: "2026-09-01T00:00:00Z",
  target: null,
};

describe("useAssignmentList", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("マウント時にapiClient.getが/api/assignmentsで呼ばれ、assignmentsにセットされる", async () => {
    mockedApiClient.get.mockResolvedValue({ assignments: [listItem] });

    const { result } = renderHook(() => useAssignmentList());
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignments");
    expect(result.current.assignments).toEqual([listItem]);
  });

  it("createAssignment成功時、apiClient.postが期待するペイロードで呼ばれ、一覧が再取得され、noticeが成功になる", async () => {
    mockedApiClient.get.mockResolvedValue({ assignments: [listItem] });
    mockedApiClient.post.mockResolvedValue(undefined);

    const { result } = renderHook(() => useAssignmentList());
    await act(async () => {});

    mockedApiClient.get.mockClear();

    let created = false;
    await act(async () => {
      created = await result.current.createAssignment("タイトル", "本文");
    });

    expect(created).toBe(true);
    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/assignments", {
      title: "タイトル",
      body: "本文",
    });
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/assignments");
    expect(result.current.notice).toEqual({ severity: "success", message: "課題を作成しました。" });
  });

  it("createAssignment失敗時、noticeがエラーになりfalseを返す", async () => {
    mockedApiClient.get.mockResolvedValue({ assignments: [] });
    mockedApiClient.post.mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => useAssignmentList());
    await act(async () => {});

    let created = true;
    await act(async () => {
      created = await result.current.createAssignment("タイトル", "本文");
    });

    expect(created).toBe(false);
    expect(result.current.notice).toEqual({
      severity: "error",
      message: "課題の作成に失敗しました。時間をおいて再度お試しください。",
    });
  });

  it("notice表示後5秒経過すると自動的にnullに戻る", async () => {
    vi.useFakeTimers();
    mockedApiClient.get.mockResolvedValue({ assignments: [] });
    mockedApiClient.post.mockResolvedValue(undefined);

    const { result } = renderHook(() => useAssignmentList());
    await act(async () => {});

    await act(async () => {
      await result.current.createAssignment("タイトル", "本文");
    });
    expect(result.current.notice).not.toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(result.current.notice).toBeNull();
  });
});
