import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useStrengthsPoc } from "./useStrengthsPoc";
import { apiClient } from "../../lib/apiClient";
import type { PocPersonaOption, PocRunDetail, PocRunSummary } from "../../lib/types";

vi.mock("../../lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
  },
}));

const mockedApiClient = vi.mocked(apiClient);

const persona: PocPersonaOption = {
  personaKey: "sql_strong_doc_weak",
  label: "SQLが強くドキュメントが弱い新人",
  description: "既知ペルソナを注入したシナリオ",
};

const runSummary: PocRunSummary = {
  id: "run_0001",
  personaKey: "sql_strong_doc_weak",
  subjectId: "emp_001",
  label: "SQLが強くドキュメントが弱い新人",
  injectedPersona: "SQL/データ処理が強くドキュメントが弱い新人",
  status: "completed",
  createdAt: "2026-09-24T00:00:00Z",
};

const runDetail = { ...runSummary, strengths: { strengths: [] } } as unknown as PocRunDetail;

/** 初期ロード(persona一覧・run一覧・run詳細)の応答を組み立てる。 */
function mockInitialLoad(runs: PocRunSummary[]) {
  mockedApiClient.get.mockImplementation(async (path: string) => {
    if (path === "/api/poc/personas") return { personas: [persona] };
    if (path === "/api/poc/runs") return { runs };
    return runDetail;
  });
}

describe("useStrengthsPoc", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("マウント時にペルソナ一覧とrun一覧を取得し、先頭のペルソナが選択される", async () => {
    mockInitialLoad([]);

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/poc/personas");
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/poc/runs");
    expect(result.current.personas).toEqual([persona]);
    expect(result.current.selectedPersonaKey).toBe("sql_strong_doc_weak");
    expect(result.current.detail).toBeNull();
  });

  it("既存のrunがある場合、最新のrun詳細が初期表示される", async () => {
    mockInitialLoad([runSummary]);

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/poc/runs/run_0001");
    expect(result.current.detail).toEqual(runDetail);
  });

  it("ペルソナが1件も無い場合、選択キーは空文字のままになる", async () => {
    mockedApiClient.get.mockImplementation(async (path: string) =>
      path === "/api/poc/personas" ? { personas: [] } : { runs: [] },
    );

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    expect(result.current.selectedPersonaKey).toBe("");
  });

  it("初期ロードに失敗した場合、エラー通知が表示される", async () => {
    mockedApiClient.get.mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    expect(result.current.notice).toEqual({
      severity: "error",
      message: "データの取得に失敗しました。",
    });
  });

  it("startRunで選択中のペルソナがPOSTされ、結果の表示とrun一覧の再取得が行われる", async () => {
    mockInitialLoad([]);
    mockedApiClient.post.mockResolvedValue(runDetail);

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});
    mockedApiClient.get.mockClear();
    mockInitialLoad([runSummary]);

    await act(async () => {
      await result.current.startRun();
    });

    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/poc/runs", {
      personaKey: "sql_strong_doc_weak",
    });
    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/poc/runs");
    expect(result.current.detail).toEqual(runDetail);
    expect(result.current.runs).toEqual([runSummary]);
    expect(result.current.notice).toEqual({
      severity: "success",
      message: "解析が完了しました。（run_0001）",
    });
    expect(result.current.running).toBe(false);
  });

  it("startRunが失敗した場合、エラー通知が表示され実行中フラグが戻る", async () => {
    mockInitialLoad([]);
    mockedApiClient.post.mockRejectedValue(new Error("network error"));

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    await act(async () => {
      await result.current.startRun();
    });

    expect(result.current.notice).toEqual({
      severity: "error",
      message: "解析の実行に失敗しました。時間をおいて再度お試しください。",
    });
    expect(result.current.running).toBe(false);
  });

  it("ペルソナ未選択のときstartRunは何もしない", async () => {
    mockedApiClient.get.mockImplementation(async (path: string) =>
      path === "/api/poc/personas" ? { personas: [] } : { runs: [] },
    );

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    await act(async () => {
      await result.current.startRun();
    });

    expect(mockedApiClient.post).not.toHaveBeenCalled();
  });

  it("setSelectedPersonaKeyで選択中のペルソナを切り替えられる", async () => {
    mockInitialLoad([]);

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    act(() => {
      result.current.setSelectedPersonaKey("ambiguous_signal");
    });

    expect(result.current.selectedPersonaKey).toBe("ambiguous_signal");
  });

  it("selectRunで過去のrunの詳細を取得して表示できる", async () => {
    mockInitialLoad([]);

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    await act(async () => {
      await result.current.selectRun("run_0002");
    });

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/poc/runs/run_0002");
    expect(result.current.detail).toEqual(runDetail);
  });

  it("selectRunが失敗した場合、エラー通知が表示される", async () => {
    mockInitialLoad([]);

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    mockedApiClient.get.mockRejectedValue(new Error("network error"));
    await act(async () => {
      await result.current.selectRun("run_0002");
    });

    expect(result.current.notice).toEqual({
      severity: "error",
      message: "解析結果の取得に失敗しました。",
    });
  });

  it("notice表示後5秒経過すると自動的にnullに戻る", async () => {
    vi.useFakeTimers();
    mockInitialLoad([]);
    mockedApiClient.post.mockResolvedValue(runDetail);

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    await act(async () => {
      await result.current.startRun();
    });
    expect(result.current.notice).not.toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(result.current.notice).toBeNull();
  });

  it("setNoticeで通知を手動で閉じられる", async () => {
    mockInitialLoad([]);

    const { result } = renderHook(() => useStrengthsPoc());
    await act(async () => {});

    act(() => {
      result.current.setNotice({ severity: "success", message: "テスト" });
    });
    expect(result.current.notice).not.toBeNull();

    act(() => {
      result.current.setNotice(null);
    });
    expect(result.current.notice).toBeNull();
  });
});
