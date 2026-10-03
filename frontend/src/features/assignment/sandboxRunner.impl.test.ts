import { afterEach, describe, expect, it, vi } from "vitest";
import { runJavaScript } from "./sandboxRunner";

function send(frame: HTMLIFrameElement, data: unknown) {
  window.dispatchEvent(new MessageEvent("message", { source: frame.contentWindow, data }));
}

describe("隔離されたJavaScript実行ランナー", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    document.querySelectorAll("iframe").forEach((frame) => frame.remove());
  });

  it("不透明オリジンと通信禁止CSPのframeだけで実行し、完了時に破棄する", async () => {
    const pending = runJavaScript("console.log('hello')");
    const frame = document.querySelector("iframe")!;
    expect(frame.getAttribute("sandbox")).toBe("allow-scripts");
    expect(frame.srcdoc).toContain("connect-src 'none'");
    expect(frame.srcdoc).toContain("worker-src blob:");
    const bootstrap = frame.srcdoc.match(/<script>([\s\S]*)<\/script>/)?.[1];
    expect(bootstrap).toBeDefined();
    expect(() => new Function(bootstrap!)).not.toThrow();
    const workerScript = bootstrap!.match(/const workerSource = `([\s\S]*?)`;/)?.[1];
    expect(workerScript).toBeDefined();
    expect(() => new Function(workerScript!)).not.toThrow();
    const post = vi.spyOn(frame.contentWindow!, "postMessage");
    send(frame, null);
    window.dispatchEvent(new MessageEvent("message", { source: window, data: { type: "ready" } }));
    expect(post).not.toHaveBeenCalled();
    send(frame, { type: "ready" });
    const request = post.mock.calls[0][0] as { id: string; code: string };
    expect(request.code).toBe("console.log('hello')");
    send(frame, { type: "output", id: "wrong", value: "ignore" });
    send(frame, { type: "output", id: request.id, value: "hello" });
    send(frame, { type: "error", id: request.id, value: "sample error" });
    send(frame, { type: "done", id: request.id });
    expect(await pending).toEqual({ output: ["hello", "sample error"], timedOut: false });
    expect(document.querySelector("iframe")).toBeNull();
  });

  it("2秒を超える実行を終了する", async () => {
    vi.useFakeTimers();
    const pending = runJavaScript("while (true) {}");
    await vi.advanceTimersByTimeAsync(2000);
    expect(await pending).toEqual({
      output: ["実行時間の上限（2秒）に達したため停止しました。"], timedOut: true,
    });
    expect(document.querySelector("iframe")).toBeNull();
  });

  it("コード量と出力量を制限する", async () => {
    expect(await runJavaScript("x".repeat(32769))).toEqual({
      output: ["コードは32,768文字以内にしてください。"], timedOut: false,
    });
    expect(document.querySelector("iframe")).toBeNull();
    const pending = runJavaScript("print('x')");
    const frame = document.querySelector("iframe")!;
    const post = vi.spyOn(frame.contentWindow!, "postMessage");
    send(frame, { type: "ready" });
    const request = post.mock.calls[0][0] as { id: string };
    for (let index = 0; index < 100; index += 1) {
      send(frame, { type: "output", id: request.id, value: "x" });
    }
    const result = await pending;
    expect(result.output).toHaveLength(101);
    expect(result.output[100]).toContain("100行");
    expect(document.querySelector("iframe")).toBeNull();
  });
});
