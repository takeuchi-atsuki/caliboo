import { describe, it, expect, vi, afterEach } from "vitest";

import { apiClient, ApiError, setUnauthorizedHandler } from "./apiClient";

function mockFetchResponse(options: { ok: boolean; status: number; json?: () => Promise<unknown> }) {
  const { ok, status, json } = options;
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: json ?? (async () => ({})),
  });
}

describe("apiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    setUnauthorizedHandler(null);
  });

  it("get(path) が相対パス・Content-Type・credentials:same-originでfetchを呼び、レスポンスJSONを返す", async () => {
    const responseBody = { message: "ok" };
    const fetchMock = mockFetchResponse({ ok: true, status: 200, json: async () => responseBody });
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiClient.get<typeof responseBody>("/api/path");

    expect(fetchMock).toHaveBeenCalledWith("/api/path", {
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
    });
    expect(result).toEqual(responseBody);
  });

  it("post(path, body) がPOSTメソッド・JSON化されたbody・credentialsでfetchを呼ぶ", async () => {
    const responseBody = { id: "1" };
    const fetchMock = mockFetchResponse({ ok: true, status: 200, json: async () => responseBody });
    vi.stubGlobal("fetch", fetchMock);
    const requestBody = { foo: "bar" };

    const result = await apiClient.post<typeof responseBody>("/api/path", requestBody);

    expect(fetchMock).toHaveBeenCalledWith("/api/path", {
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      method: "POST",
      body: JSON.stringify(requestBody),
    });
    expect(result).toEqual(responseBody);
  });

  it("del(path) がDELETEメソッド・credentialsでfetchを呼ぶ", async () => {
    const fetchMock = mockFetchResponse({ ok: true, status: 204 });
    vi.stubGlobal("fetch", fetchMock);

    await apiClient.del("/api/path/1");

    expect(fetchMock).toHaveBeenCalledWith("/api/path/1", {
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      method: "DELETE",
    });
  });

  it("レスポンスが204の場合、undefinedを返す", async () => {
    const jsonFn = vi.fn().mockResolvedValue({ unexpected: true });
    const fetchMock = mockFetchResponse({ ok: true, status: 204, json: jsonFn });
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiClient.get("/api/path");

    expect(result).toBeUndefined();
    expect(jsonFn).not.toHaveBeenCalled();
  });

  it("レスポンスが非2xx(404)の場合、statusを持つApiErrorをthrowする(getはmethod表示がGET)", async () => {
    const fetchMock = mockFetchResponse({ ok: false, status: 404 });
    vi.stubGlobal("fetch", fetchMock);

    const error: unknown = await apiClient.get("/api/not-found").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).message).toBe("API request failed: GET /api/not-found (404)");
  });

  it("レスポンスが非2xx(500)の場合、statusを持つApiErrorをthrowする", async () => {
    const fetchMock = mockFetchResponse({ ok: false, status: 500 });
    vi.stubGlobal("fetch", fetchMock);

    const error: unknown = await apiClient.post("/api/path", { foo: "bar" }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(500);
    expect((error as ApiError).message).toBe("API request failed: POST /api/path (500)");
  });

  it("401を受けた場合、登録済みの401ハンドラを呼ぶ", async () => {
    const fetchMock = mockFetchResponse({ ok: false, status: 401 });
    vi.stubGlobal("fetch", fetchMock);
    const handler = vi.fn();
    setUnauthorizedHandler(handler);

    await expect(apiClient.get("/api/assignments")).rejects.toBeInstanceOf(ApiError);

    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("401でもパスが/api/auth/で始まる場合はハンドラを呼ばない(ログイン失敗表示と競合させないため)", async () => {
    const fetchMock = mockFetchResponse({ ok: false, status: 401 });
    vi.stubGlobal("fetch", fetchMock);
    const handler = vi.fn();
    setUnauthorizedHandler(handler);

    await expect(
      apiClient.post("/api/auth/login", { loginId: "x", password: "y" }),
    ).rejects.toBeInstanceOf(ApiError);

    expect(handler).not.toHaveBeenCalled();
  });

  it("ハンドラ未設定の場合でも401はApiErrorとしてthrowされるだけで、呼び出し自体は例外にならない", async () => {
    const fetchMock = mockFetchResponse({ ok: false, status: 401 });
    vi.stubGlobal("fetch", fetchMock);

    const error: unknown = await apiClient.get("/api/assignments").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(401);
  });
});
