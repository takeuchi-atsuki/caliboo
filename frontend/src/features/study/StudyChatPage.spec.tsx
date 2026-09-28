import type { ReactNode } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { StudyChatPage } from "./StudyChatPage";
import { useStudyChat } from "./useStudyChat";

vi.mock("../../components/layout/PageContainer", () => ({
  PageContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock("../../components/chat/ChatMessageList", () => ({ ChatMessageList: () => null }));
vi.mock("./useStudyChat", () => ({ useStudyChat: vi.fn() }));
const retry = vi.fn();
const sendMessage = vi.fn();
const base = { relatedQuestions: [], relatedError: null, messages: [], input: "質問", setInput: vi.fn(),
  sendMessage, quickQuestions: [], sending: false, error: null, canRetry: false, retry };

beforeEach(() => { vi.resetAllMocks(); vi.mocked(useStudyChat).mockReturnValue(base); });

it("問題の失敗を表示して再送でき、入力も利用できる", () => {
  vi.mocked(useStudyChat).mockReturnValue({ ...base, error: "回答を取得できませんでした。", canRetry: true });
  render(<MemoryRouter><StudyChatPage /></MemoryRouter>);
  expect(screen.getByRole("alert")).toHaveTextContent("回答を取得できませんでした");
  fireEvent.click(screen.getByRole("button", { name: "再送する" }));
  expect(retry).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole("button", { name: "送信" }));
  expect(sendMessage).toHaveBeenCalledWith("質問");
});

it("回答の待ち状態を示し、問題引継ぎをフックへ渡す", () => {
  vi.mocked(useStudyChat).mockReturnValue({ ...base, sending: true });
  const question = { text: "問題文", choices: ["A", "B"] };
  render(<MemoryRouter initialEntries={[{ pathname: "/study/chat", state: { quizQuestion: question } }]}>
    <StudyChatPage />
  </MemoryRouter>);
  expect(screen.getByRole("status")).toHaveTextContent("回答を考えています");
  expect(useStudyChat).toHaveBeenCalledWith(question);
  expect(useStudyChat).toHaveBeenLastCalledWith(null);
});
