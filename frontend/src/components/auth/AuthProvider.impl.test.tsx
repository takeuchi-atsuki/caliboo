import { useState } from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AuthProvider, useAuth, ROLE_LABEL } from "./AuthProvider";
import { apiClient, ApiError, setUnauthorizedHandler } from "../../lib/apiClient";
import { clearAutosave } from "../../features/report/reportAutosave";
import type { CurrentUser } from "../../lib/types";

vi.mock("../../lib/apiClient", () => {
  class MockApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  }
  return {
    apiClient: { get: vi.fn(), post: vi.fn(), del: vi.fn() },
    ApiError: MockApiError,
    setUnauthorizedHandler: vi.fn(),
  };
});

vi.mock("../../features/report/reportAutosave", () => ({
  clearAutosave: vi.fn(),
}));

const mockedApiClient = vi.mocked(apiClient);
const mockedSetUnauthorizedHandler = vi.mocked(setUnauthorizedHandler);
const mockedClearAutosave = vi.mocked(clearAutosave);

const currentUser: CurrentUser = { id: 1, loginId: "yuki", displayName: "ユウキ", role: "member" };

function Probe() {
  const { status, user, loggedOutByUser, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="user">{user?.displayName ?? ""}</span>
      <span data-testid="loggedOutByUser">{String(loggedOutByUser)}</span>
      <button onClick={() => login("yuki", "caliboo-yuki")}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

function LoginErrorProbe() {
  const { status, login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="error">{error ?? ""}</span>
      <button
        onClick={async () => {
          try {
            await login("yuki", "wrong-password");
          } catch (e) {
            setError(e instanceof Error ? e.message : "unknown");
          }
        }}
      >
        login
      </button>
    </div>
  );
}

describe("AuthProvider", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("マウント時にGET /api/auth/meが成功するとauthenticatedになりuserが設定される", async () => {
    mockedApiClient.get.mockResolvedValue(currentUser);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    expect(mockedApiClient.get).toHaveBeenCalledWith("/api/auth/me");
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
    expect(screen.getByTestId("user").textContent).toBe("ユウキ");
  });

  it("マウント時にGET /api/auth/meが401で失敗するとunauthenticatedになる", async () => {
    mockedApiClient.get.mockRejectedValue(new ApiError(401, "not authenticated"));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
    expect(screen.getByTestId("user").textContent).toBe("");
  });

  it("マウント時にapiClientへ401ハンドラを登録する", async () => {
    mockedApiClient.get.mockResolvedValue(currentUser);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
    expect(mockedSetUnauthorizedHandler).toHaveBeenCalledWith(expect.any(Function));
  });

  it("login成功時、apiClient.postが期待するペイロードで呼ばれauthenticatedになる", async () => {
    mockedApiClient.get.mockRejectedValue(new ApiError(401, "not authenticated"));
    mockedApiClient.post.mockResolvedValue(currentUser);
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));

    await user.click(screen.getByText("login"));

    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/auth/login", {
      loginId: "yuki",
      password: "caliboo-yuki",
    });
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
    expect(screen.getByTestId("user").textContent).toBe("ユウキ");
  });

  it("login失敗時、エラーがthrowされstatusはunauthenticatedのまま", async () => {
    mockedApiClient.get.mockRejectedValue(new ApiError(401, "not authenticated"));
    mockedApiClient.post.mockRejectedValue(new ApiError(401, "invalid login id or password"));
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <LoginErrorProbe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));

    await user.click(screen.getByText("login"));

    await waitFor(() => expect(screen.getByTestId("error").textContent).not.toBe(""));
    expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
  });

  it("logoutでapiClient.postが呼ばれ、clearAutosaveが呼ばれ、unauthenticatedになる", async () => {
    mockedApiClient.get.mockResolvedValue(currentUser);
    mockedApiClient.post.mockResolvedValue(undefined);
    sessionStorage.setItem("caliboo.assignment-workspace.1.10", "saved code");
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

    await user.click(screen.getByText("logout"));

    expect(mockedApiClient.post).toHaveBeenCalledWith("/api/auth/logout", undefined);
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
    expect(mockedClearAutosave).toHaveBeenCalled();
    expect(sessionStorage.getItem("caliboo.assignment-workspace.1.10")).toBeNull();
    expect(screen.getByTestId("loggedOutByUser").textContent).toBe("true");
  });

  it("logout後に再度loginすると、loggedOutByUserがfalseに戻る", async () => {
    mockedApiClient.get.mockResolvedValue(currentUser);
    mockedApiClient.post.mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
    await user.click(screen.getByText("logout"));
    await waitFor(() => expect(screen.getByTestId("loggedOutByUser").textContent).toBe("true"));

    mockedApiClient.post.mockResolvedValue(currentUser);
    await user.click(screen.getByText("login"));

    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
    expect(screen.getByTestId("loggedOutByUser").textContent).toBe("false");
  });

  it("他のAPIの401ハンドラが呼ばれると、unauthenticatedへ遷移する", async () => {
    mockedApiClient.get.mockResolvedValue(currentUser);
    sessionStorage.setItem("caliboo.assignment-workspace.1.10", "saved code");

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));

    const calls = mockedSetUnauthorizedHandler.mock.calls;
    const registeredHandler = calls[calls.length - 1]?.[0];
    expect(typeof registeredHandler).toBe("function");

    act(() => {
      registeredHandler?.();
    });

    expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
    expect(sessionStorage.getItem("caliboo.assignment-workspace.1.10")).toBeNull();
    expect(screen.getByTestId("user").textContent).toBe("");
    expect(screen.getByTestId("loggedOutByUser").textContent).toBe("false");
  });

  it("Provider外でuseAuth()を呼ぶとエラーになる", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow("useAuth must be used within AuthProvider");
    consoleErrorSpy.mockRestore();
  });

  it("ROLE_LABELがmember/adminの表示名を持つ", () => {
    expect(ROLE_LABEL.member).toBe("新入社員");
    expect(ROLE_LABEL.admin).toBe("講師");
  });
});
