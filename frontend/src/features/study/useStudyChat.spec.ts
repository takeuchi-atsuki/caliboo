import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { apiClient } from "../../lib/apiClient";
import type { ChatMessage } from "../../lib/types";
import { useStudyChat } from "./useStudyChat";
import type { QuizHandoff } from "./quizHandoff";

vi.mock("../../lib/apiClient", () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
const reply: ChatMessage = { id: "answer", role: "bot", text: "比較する条件を確認しましょう。", references: [] };
const handoff: QuizHandoff = { text: "問題文", choices: ["ア", "イ"] };
const related = [{ id: "r1", title: "過去問", questionCount: 3, tags: [] }];

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(apiClient.get).mockResolvedValue({ items: related });
  vi.mocked(apiClient.post).mockResolvedValue(reply);
});

it("初期表示と空送信・再送対象なし", async () => {
  const { result } = renderHook(() => useStudyChat());
  await waitFor(() => expect(result.current.relatedQuestions).toEqual(related));
  await act(async () => { await result.current.sendMessage("  "); await result.current.retry(); });
  expect(apiClient.post).not.toHaveBeenCalled();
  expect(result.current.messages).toHaveLength(1);
  expect(result.current.canRetry).toBe(false);
});

it("成功した質問と回答を追加し、直近12発言を次の文脈に使う", async () => {
  const { result } = renderHook(() => useStudyChat());
  await waitFor(() => expect(result.current.relatedQuestions).toHaveLength(1));
  for (let index = 0; index < 8; index++) {
    await act(async () => result.current.sendMessage(`質問${index}`));
  }
  expect(apiClient.post).toHaveBeenNthCalledWith(1, "/api/study/chat", { text: "質問0", history: [] });
  const payload = vi.mocked(apiClient.post).mock.calls.slice(-1)[0][1] as { history: unknown[] };
  expect(payload.history).toHaveLength(12);
  expect(payload.history[0]).toEqual({ role: "me", text: "質問1" });
  expect(result.current.messages).toHaveLength(17);
  expect(result.current.input).toBe("");
});

it("失敗した送信は会話に重複せず、入力と過去履歴を保って再送", async () => {
  const { result } = renderHook(() => useStudyChat());
  await waitFor(() => expect(result.current.relatedQuestions).toHaveLength(1));
  await act(async () => result.current.sendMessage("前の質問"));
  vi.mocked(apiClient.post).mockRejectedValueOnce(new Error("unavailable"));
  await act(async () => result.current.sendMessage("現在の質問"));
  expect(result.current.error).toContain("再送");
  expect(result.current.input).toBe("現在の質問");
  expect(result.current.messages).toHaveLength(3);
  await act(async () => result.current.retry());
  expect(result.current.messages).toHaveLength(5);
  expect(result.current.messages.filter((message) => message.text === "現在の質問")).toHaveLength(1);
  expect(result.current.error).toBeNull();
  expect(vi.mocked(apiClient.post).mock.calls.slice(-1)[0][1]).toEqual({ text: "現在の質問", history: [
    { role: "me", text: "前の質問" }, { role: "bot", text: reply.text },
  ] });
});

it.each([false, true])("問題引継ぎを1回だけ送信し、state消去後も文脈を保持 StrictMode=%s", async (strict) => {
  const { result, rerender } = renderHook(({ value }) => useStudyChat(value), {
    initialProps: { value: handoff as QuizHandoff | null }, reactStrictMode: strict,
  });
  await waitFor(() => expect(result.current.messages).toHaveLength(3));
  expect(apiClient.post).toHaveBeenCalledTimes(1);
  expect(result.current.messages[1].text).toContain("問題文");
  expect(result.current.messages[2]).toEqual(reply);
  rerender({ value: null });
  await act(async () => result.current.sendMessage("なぜ？"));
  expect(vi.mocked(apiClient.post).mock.calls.slice(-1)[0][1]).toEqual(expect.objectContaining({ question: handoff }));
  expect(result.current.messages).toHaveLength(5);
});

it("引継ぎの失敗を再送し、最初の質問を二重に表示しない", async () => {
  vi.mocked(apiClient.post).mockRejectedValueOnce(new Error());
  const { result } = renderHook(() => useStudyChat(handoff));
  await waitFor(() => expect(result.current.canRetry).toBe(true));
  expect(result.current.messages).toHaveLength(2);
  await act(async () => result.current.retry());
  expect(result.current.messages).toHaveLength(3);
});

it("処理中の二重送信を抑止し、別の入力を消さない", async () => {
  let finish!: (value: ChatMessage) => void;
  vi.mocked(apiClient.post).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  const { result } = renderHook(() => useStudyChat());
  await waitFor(() => expect(result.current.relatedQuestions).toHaveLength(1));
  let pending!: Promise<void>;
  act(() => { pending = result.current.sendMessage("送信中"); });
  expect(result.current.sending).toBe(true);
  await act(async () => result.current.sendMessage("二重"));
  act(() => result.current.setInput("次に聞く質問"));
  await act(async () => { finish(reply); await pending; });
  expect(apiClient.post).toHaveBeenCalledTimes(1);
  expect(result.current.input).toBe("次に聞く質問");
});

it.each([false, true])("離脱後の回答と失敗を破棄 %s", async (fail) => {
  let finish!: (value: unknown) => void;
  vi.mocked(apiClient.post).mockImplementationOnce(() => new Promise((resolve, reject) => { finish = fail ? reject : resolve; }));
  const { result, unmount } = renderHook(() => useStudyChat());
  await waitFor(() => expect(result.current.relatedQuestions).toHaveLength(1));
  let pending!: Promise<void>;
  act(() => { pending = result.current.sendMessage("質問"); });
  unmount();
  await act(async () => { finish(fail ? new Error() : reply); await pending; });
  await act(async () => result.current.sendMessage("離脱後"));
  expect(result.current.messages).toHaveLength(1);
  expect(apiClient.post).toHaveBeenCalledTimes(1);
});

it("関連問題の取得失敗でも会話を送れる", async () => {
  vi.mocked(apiClient.get).mockRejectedValue(new Error());
  const { result } = renderHook(() => useStudyChat());
  await waitFor(() => expect(result.current.relatedError).toContain("質問は送信できます"));
  await act(async () => result.current.sendMessage("質問"));
  expect(result.current.messages).toHaveLength(3);
});

it.each([false, true])("離脱後の関連問題の成功・失敗を破棄 %s", async (fail) => {
  let finish!: (value: unknown) => void;
  vi.mocked(apiClient.get).mockImplementationOnce(() => new Promise((resolve, reject) => { finish = fail ? reject : resolve; }));
  const { result, unmount } = renderHook(() => useStudyChat());
  unmount();
  await act(async () => finish(fail ? new Error() : { items: related }));
  expect(result.current.relatedQuestions).toEqual([]);
  expect(result.current.relatedError).toBeNull();
});


it("通常送信の失敗後に編集した入力を再送する", async () => {
  vi.mocked(apiClient.post).mockRejectedValueOnce(new Error());
  const { result } = renderHook(() => useStudyChat());
  await waitFor(() => expect(result.current.relatedQuestions).toHaveLength(1));
  await act(async () => result.current.sendMessage("元の質問"));
  act(() => result.current.setInput("書き直した質問"));
  await act(async () => result.current.retry());
  expect(apiClient.post).toHaveBeenLastCalledWith("/api/study/chat", { text: "書き直した質問", history: [] });
  expect(result.current.messages[1].text).toBe("書き直した質問");
});
