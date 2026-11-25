import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "../../App";
import { apiClient } from "../../lib/apiClient";
import type { AssignmentDetail, CurrentUser } from "../../lib/types";

vi.mock("../../lib/apiClient", () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
  setUnauthorizedHandler: vi.fn(),
}));

const member: CurrentUser = { id: 42, loginId: "test-member", displayName: "テスト新入社員", role: "member" };
const assignment: AssignmentDetail = {
  id: 73, title: "個人向け確認課題", body: "合成データの課題本文", status: "not_submitted",
  createdAt: "2026-11-25", target: { id: member.id, displayName: member.displayName },
  submission: null, messageForMember: null,
};
const submitted: AssignmentDetail = {
  ...assignment, status: "submitted", submission: { answerText: "確認しました", submittedAt: "2026-11-25" },
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal("matchMedia", vi.fn().mockImplementation((query: string) => ({
    matches: false, media: query, addEventListener: vi.fn(), removeEventListener: vi.fn(),
  })));
  window.history.replaceState(null, "", "/strengths");
  let current = assignment;
  vi.mocked(apiClient.get).mockImplementation(async (path) => {
    switch (path) {
      case "/api/auth/me": return member;
      case "/api/development/strengths": return { candidates: [], jobs: [] };
      case "/api/development/actions": return { actions: [], assignments: [current] };
      case "/api/assignments": return { assignments: [current] };
      case `/api/assignments/${assignment.id}`: return current;
      default: throw new Error(`Unexpected API request: ${path}`);
    }
  });
  vi.mocked(apiClient.post).mockImplementation(async (path) => {
    if (path !== `/api/assignments/${assignment.id}/submission`) throw new Error(`Unexpected API request: ${path}`);
    current = submitted;
    return current;
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

it("本人が強み画面の配信課題から詳細へ進み、提出後も一覧から同じ課題を開ける", async () => {
  const user = userEvent.setup();
  render(<App />);
  expect(await screen.findByRole("heading", { name: "配信された課題" })).toBeVisible();
  await user.click(await screen.findByRole("link", { name: assignment.title }));

  expect(window.location.pathname).toBe(`/assignments/${assignment.id}`);
  expect(await screen.findByText(assignment.body)).toBeVisible();
  expect(apiClient.get).toHaveBeenCalledWith(`/api/assignments/${assignment.id}`);
  await user.type(screen.getByPlaceholderText("ここに回答を記入してください"), "確認しました");
  await user.click(screen.getByRole("button", { name: "提出する" }));
  expect(await screen.findByText("回答を提出しました。")).toBeVisible();
  expect(apiClient.post).toHaveBeenCalledWith(`/api/assignments/${assignment.id}/submission`, { answerText: "確認しました" });

  await user.click(screen.getByRole("link", { name: "課題一覧に戻る" }));
  expect(window.location.pathname).toBe("/assignments");
  await user.click(await screen.findByRole("link", { name: assignment.title }));
  expect(window.location.pathname).toBe(`/assignments/${assignment.id}`);
  expect(await screen.findByRole("button", { name: "再提出する" })).toBeVisible();
  expect(screen.getByPlaceholderText("ここに回答を記入してください")).toHaveValue("確認しました");
});
