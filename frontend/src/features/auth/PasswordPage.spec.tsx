import { afterEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { PasswordPage } from "./PasswordPage";
import { useAuth } from "../../components/auth/AuthProvider";
import { apiClient } from "../../lib/apiClient";

vi.mock("../../components/auth/AuthProvider", () => ({ useAuth: vi.fn() }));
vi.mock("../../components/layout/PageContainer", () => ({
  PageContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("../../lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/apiClient")>();
  return { ...actual, apiClient: { ...actual.apiClient, post: vi.fn() } };
});

const mockedPost = vi.mocked(apiClient.post);
const mockedUseAuth = vi.mocked(useAuth);

afterEach(() => vi.clearAllMocks());

it("確認欄が一致したときだけ再設定し、成功を表示する", async () => {
  mockedUseAuth.mockReturnValue({ logout: vi.fn() } as unknown as ReturnType<typeof useAuth>);
  mockedPost.mockResolvedValue(undefined);
  render(<MemoryRouter><PasswordPage mode="reset" /></MemoryRouter>);
  fireEvent.change(screen.getByRole("textbox", { name: "ログインID" }), { target: { value: "yuki" } });
  fireEvent.change(screen.getByRole("textbox", { name: "再設定コード" }), { target: { value: "code" } });
  fireEvent.change(screen.getAllByLabelText(/新しいパスワード/)[0], { target: { value: "new-password-123" } });
  fireEvent.change(screen.getAllByLabelText(/新しいパスワード/)[1], { target: { value: "wrong-password" } });
  fireEvent.click(screen.getByRole("button", { name: "更新する" }));
  expect(mockedPost).not.toHaveBeenCalled();
  expect(screen.getByText("新しいパスワードが一致しません。")).toBeInTheDocument();
  fireEvent.change(screen.getAllByLabelText(/新しいパスワード/)[1], { target: { value: "new-password-123" } });
  fireEvent.click(screen.getByRole("button", { name: "更新する" }));
  await waitFor(() => expect(mockedPost).toHaveBeenCalledWith("/api/auth/reset-password", {
    loginId: "yuki", resetCode: "code", newPassword: "new-password-123",
  }));
  expect(await screen.findByText(/パスワードを更新しました/)).toBeInTheDocument();
});

it("本人の変更後にログアウトする", async () => {
  const logout = vi.fn().mockResolvedValue(undefined);
  mockedUseAuth.mockReturnValue({ logout } as unknown as ReturnType<typeof useAuth>);
  mockedPost.mockResolvedValue(undefined);
  render(<MemoryRouter><PasswordPage mode="change" /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText(/現在のパスワード/), { target: { value: "caliboo-yuki" } });
  fireEvent.change(screen.getAllByLabelText(/新しいパスワード/)[0], { target: { value: "new-password-123" } });
  fireEvent.change(screen.getAllByLabelText(/新しいパスワード/)[1], { target: { value: "new-password-123" } });
  fireEvent.click(screen.getByRole("button", { name: "更新する" }));
  await waitFor(() => expect(logout).toHaveBeenCalled());
  expect(mockedPost).toHaveBeenCalledWith("/api/auth/change-password", {
    currentPassword: "caliboo-yuki", newPassword: "new-password-123",
  });
});
