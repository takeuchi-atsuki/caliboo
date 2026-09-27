import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useStudyChat } from "./useStudyChat";
import { QUIZ_HANDOFF_REPLY, type QuizHandoff } from "./quizHandoff";
import { apiClient } from "../../lib/apiClient";
import type { ChatMessage, RelatedQuestionItem } from "../../lib/types";

vi.mock("../../lib/apiClient", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
  },
}));

const mockedApiClient = vi.mocked(apiClient);

const relatedItems: RelatedQuestionItem[] = [{ id: "r1", title: "関連過去問", questionCount: 3, tags: ["苦手"] }];

const reply: ChatMessage = { id: "study-reply-1", role: "bot", text: "回答", references: [] };

const handoff: QuizHandoff = { text: "問題文", choices: ["ア", "イ"] };

describe("useStudyChat", () => {
  beforeEach(() => {
    mockedApiClient.get.mockResolvedValue({ items: relatedItems });
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it("マウント時に関連過去問を取得し、初期botメッセージのみを表示する", async () => {
    const { result } = renderHook(() => useStudyChat());
    await act(async () => {});

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/study/related-questions");
    expect(result.current.relatedQuestions).toEqual(relatedItems);
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe("bot");
  });

  it("sendMessageで自分の発言とAPIの応答が追加され、入力欄が空になる", async () => {
    mockedApiClient.post.mockResolvedValue(reply);
    const { result } = renderHook(() => useStudyChat());
    await act(async () => {});
    act(() => result.current.setInput("質問"));

    await act(async () => {
      await result.current.sendMessage("質問");
    });

    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/study/chat", { text: "質問" });
    expect(result.current.messages.slice(1)).toEqual([expect.objectContaining({ role: "me", text: "質問" }), reply]);
    expect(result.current.input).toBe("");
    expect(result.current.sending).toBe(false);
  });

  it("空白のみのテキストは送信しない", async () => {
    const { result } = renderHook(() => useStudyChat());
    await act(async () => {});

    await act(async () => {
      await result.current.sendMessage("   ");
    });

    expect(mockedApiClient.post).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(1);
  });

  it("引き継ぎ問題があると、問題文の質問とモック回答が初期表示され、APIには送信しない", async () => {
    const { result } = renderHook(() => useStudyChat(handoff));
    await act(async () => {});

    expect(result.current.messages).toHaveLength(3);
    expect(result.current.messages[1]).toEqual(
      expect.objectContaining({ role: "me", text: "この問題がわからない：\n問題文\n\nA. ア\nB. イ" }),
    );
    expect(result.current.messages[2]).toEqual(QUIZ_HANDOFF_REPLY);
    expect(mockedApiClient.post).not.toHaveBeenCalled();
  });

  it("引き継ぎ問題がnullに変わって再レンダーしても、引き継ぎメッセージは重複も消失もしない", async () => {
    const { result, rerender } = renderHook(({ value }) => useStudyChat(value), {
      initialProps: { value: handoff as QuizHandoff | null },
    });
    await act(async () => {});

    rerender({ value: null });

    expect(result.current.messages).toHaveLength(3);
  });

  it("StrictModeでも引き継ぎメッセージは重複しない", async () => {
    const { result } = renderHook(() => useStudyChat(handoff), { reactStrictMode: true });
    await act(async () => {});

    expect(result.current.messages).toHaveLength(3);
  });
});
