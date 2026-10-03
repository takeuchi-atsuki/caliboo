/** ブラウザ内の一時実行環境。利用者のコードをアプリ本体のオリジンで実行しない。 */
export interface RunResult {
  output: string[];
  timedOut: boolean;
}

const TIME_LIMIT_MS = 2000;
const MAX_OUTPUT_LINES = 100;
const MAX_CODE_LENGTH = 32768;

// !NOTE: sandbox iframeにはallow-same-originを付けない。iframe内のWorkerも不透明な
// オリジンで動き、connect-src 'none'でネットワークを禁止する。Workerを破棄すれば
// 無限ループも停止でき、アプリのCookie・localStorage・DOMを渡さずに実行できる。
const FRAME_DOCUMENT = `<!doctype html><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' blob:; worker-src blob:; connect-src 'none'; form-action 'none'; base-uri 'none'">
<script>
const workerSource = \`self.onmessage = async (event) => {
  const send = (type, value) => self.postMessage({ type, value: String(value).slice(0, 4096) });
  const output = (...values) => send('output', values.map(String).join(' '));
  try {
    const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
    const fn = new AsyncFunction('console', 'print', event.data.code);
    const result = await fn({ log: output, warn: output, error: output }, output);
    if (result !== undefined) output(result);
  } catch (error) {
    send('error', error && error.message ? error.message : error);
  }
  send('done', '');
};\`;
window.addEventListener('message', (event) => {
  if (event.source !== parent || event.data?.kind !== 'run') return;
  try {
    const url = URL.createObjectURL(new Blob([workerSource], { type: 'text/javascript' }));
    const worker = new Worker(url);
    URL.revokeObjectURL(url);
    worker.onmessage = ({ data }) => parent.postMessage({ ...data, id: event.data.id }, '*');
    worker.onerror = () => {
      parent.postMessage({ type: 'error', value: '実行環境を開始できませんでした。', id: event.data.id }, '*');
      parent.postMessage({ type: 'done', id: event.data.id }, '*');
    };
    worker.postMessage({ code: event.data.code });
  } catch {
    parent.postMessage({ type: 'error', value: '実行環境を開始できませんでした。', id: event.data.id }, '*');
    parent.postMessage({ type: 'done', id: event.data.id }, '*');
  }
});
parent.postMessage({ type: 'ready' }, '*');
</script>`;

export function runJavaScript(code: string): Promise<RunResult> {
  if (code.length > MAX_CODE_LENGTH) {
    return Promise.resolve({ output: ["コードは32,768文字以内にしてください。"], timedOut: false });
  }
  return new Promise((resolve) => {
    const frame = document.createElement("iframe");
    frame.setAttribute("sandbox", "allow-scripts");
    frame.setAttribute("aria-hidden", "true");
    frame.style.display = "none";
    const id = crypto.randomUUID();
    const output: string[] = [];
    let finished = false;
    function finish(timedOut: boolean) {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      window.removeEventListener("message", onMessage);
      frame.remove();
      resolve({ output, timedOut });
    }
    function onMessage(event: MessageEvent) {
      if (event.source !== frame.contentWindow) return;
      const data = event.data as { type?: string; id?: string; value?: string } | null;
      if (!data) return;
      if (data.type === "ready") {
        frame.contentWindow?.postMessage({ kind: "run", id, code }, "*");
      } else if (data.id === id && (data.type === "output" || data.type === "error")) {
        output.push(String(data.value ?? "").slice(0, 4096));
        if (output.length >= MAX_OUTPUT_LINES) {
          output.push("出力が100行に達したため停止しました。");
          finish(false);
        }
      } else if (data.id === id && data.type === "done") {
        finish(false);
      }
    }
    const timer = window.setTimeout(() => {
      output.push("実行時間の上限（2秒）に達したため停止しました。");
      finish(true);
    }, TIME_LIMIT_MS);
    window.addEventListener("message", onMessage);
    frame.srcdoc = FRAME_DOCUMENT;
    document.body.append(frame);
  });
}
