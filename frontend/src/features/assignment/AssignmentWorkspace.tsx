import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Alert, Box, Button, Stack, TextField, Typography } from "@mui/material";

import { runJavaScript } from "./sandboxRunner";
import { loadWorkspace, saveWorkspace } from "./workspaceStorage";
import { parseTerminalCommand } from "./workspaceTerminal";

interface Props {
  assignmentId: number;
  userId: number;
  canUseCode: boolean;
  onUseCode: (code: string) => void;
}

function appendLines(previous: string[], additions: string[]): string[] {
  return [...previous, ...additions].slice(-500).map((line) => line.slice(0, 4096));
}

export function AssignmentWorkspace({ assignmentId, userId, canUseCode, onUseCode }: Props) {
  const [code, setCode] = useState(() => loadWorkspace(userId, assignmentId));
  const [command, setCommand] = useState("");
  const [lines, setLines] = useState<string[]>(["main.js を編集し、run で実行できます。help でコマンドを確認できます。"]);
  const [running, setRunning] = useState(false);
  const [storageError, setStorageError] = useState(false);

  function editCode(value: string) {
    setCode(value);
    setStorageError(!saveWorkspace(userId, assignmentId, value));
  }

  async function execute(input: string) {
    const parsed = parseTerminalCommand(input);
    setCommand("");
    if (parsed.kind === "clear") {
      setLines([]);
      return;
    }
    setLines((previous) => appendLines(previous, [`$ ${input}`]));
    if (parsed.kind === "help") {
      setLines((previous) => appendLines(previous, ["help / ls / cat main.js / run / clear"]));
    } else if (parsed.kind === "list") {
      setLines((previous) => appendLines(previous, ["main.js"]));
    } else if (parsed.kind === "show") {
      setLines((previous) => appendLines(previous, [code || "（空のファイル）"]));
    } else if (parsed.kind === "error") {
      setLines((previous) => appendLines(previous, [parsed.message]));
    } else if (!code.trim()) {
      setLines((previous) => appendLines(previous, ["main.js にコードを入力してください。"]));
    } else {
      setRunning(true);
      try {
        const result = await runJavaScript(code);
        setLines((previous) => appendLines(previous, result.output.length ? result.output : ["（出力なし）"]));
      } catch {
        setLines((previous) => appendLines(previous, ["実行環境でエラーが発生しました。"]));
      } finally {
        setRunning(false);
      }
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (command.trim() && !running) void execute(command.trim());
  }

  return <Box sx={{ background: "var(--color-panel)", borderRadius: 3, p: { xs: 2, md: 3 } }}>
    <Typography component="h2" variant="h6">課題ワークスペース</Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
      ブラウザ内で JavaScript を試せます。作業内容はこのタブに一時保存され、ログアウト時に消えます。
    </Typography>
    {storageError && <Alert severity="warning" sx={{ mb: 2 }}>一時保存できません。画面を閉じる前にコードを回答欄へ反映してください。</Alert>}
    <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
      <Stack spacing={1} sx={{ flex: 1, minWidth: 0 }}>
        <Typography component="label" htmlFor="workspace-code" variant="subtitle2">main.js</Typography>
        <Box component="textarea" id="workspace-code" aria-label="main.js のコード" value={code}
          onChange={(event: ChangeEvent<HTMLTextAreaElement>) => editCode(event.target.value)} maxLength={32768}
          spellCheck={false} sx={{ width: "100%", minHeight: 240, resize: "vertical", fontFamily: "monospace", fontSize: 14,
            p: 1.5, borderRadius: 2, border: "1px solid var(--color-border)", color: "var(--color-text)", bgcolor: "var(--color-bg)" }} />
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
          <Button variant="contained" disabled={running} onClick={() => void execute("run")}>実行</Button>
          <Button variant="outlined" disabled={!canUseCode || !code.trim()} onClick={() => onUseCode(code)}>コードを回答欄へ反映</Button>
        </Stack>
      </Stack>
      <Stack spacing={1} sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="subtitle2">ターミナル</Typography>
        <Box role="log" aria-label="ターミナル出力" sx={{ minHeight: 240, maxHeight: 360, overflow: "auto", bgcolor: "#182126", color: "#ecf5ef",
          borderRadius: 2, p: 1.5, font: "13px/1.5 monospace", whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
          {lines.map((line, index) => <div key={index}>{line}</div>)}
        </Box>
        <Box component="form" onSubmit={submit}>
          <TextField fullWidth size="small" label="コマンド" value={command} disabled={running}
            slotProps={{ htmlInput: { maxLength: 100 } }}
            onChange={(event) => setCommand(event.target.value)} helperText="help でコマンド一覧を表示" />
        </Box>
      </Stack>
    </Stack>
  </Box>;
}
