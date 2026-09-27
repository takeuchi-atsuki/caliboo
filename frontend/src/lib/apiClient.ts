export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;

const AUTH_PATH_PREFIX = "/api/auth/";

/**
 * !NOTE: AuthProviderが401を検知して未ログイン状態(`/login`)へ戻すためのフック。
 *        `/api/auth/`配下(ログイン自体の失敗等)はここでは対象外にしている。
 *        ログイン失敗はLoginPageが専用のエラーメッセージを表示するため、
 *        401ハンドラによる強制遷移と表示が競合しないようにするため。
 */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...init,
  });
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith(AUTH_PATH_PREFIX)) {
      unauthorizedHandler?.();
    }
    throw new ApiError(response.status, `API request failed: ${init?.method ?? "GET"} ${path} (${response.status})`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  del: (path: string) => request<void>(path, { method: "DELETE" }),
};
