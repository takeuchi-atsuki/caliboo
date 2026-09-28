import { Alert, Button, Paper, Stack, Typography } from "@mui/material";
import { useResource } from "../../lib/useResource";
import type { AgentJob } from "../../lib/types";

const kinds = { strength: "強み解析", proposal: "課題案の再生成", proposal_initial: "個別課題案" };
const errors: Record<string, string> = {
  provider_unavailable: "生成サービスに接続できませんでした。",
  invalid_configuration: "生成サービスの設定を確認してください。",
  invalid_materials: "入力資料を確認してください。",
  invalid_result: "生成結果の引用や形式を確認できませんでした。",
  invalid_output: "生成結果の形式を確認できませんでした。",
  invalid_evidence: "生成結果の引用を確認できませんでした。",
  insufficient_materials: "提案の根拠になる資料が不足しています。",
  input_too_large: "入力資料が上限を超えています。",
  lease_expired: "処理が中断されました。",
};

export function AgentJobQueue({ enabled }: { enabled: boolean }) {
  const queue = useResource<{ jobs: AgentJob[]; provider: "manual" | "openai" }>(
    enabled ? "/api/development/jobs" : null, 5000);
  if (!enabled) return null;
  return <Stack spacing={2}>
    {queue.data && <Alert severity="info">{queue.data.provider === "openai"
      ? "解析は自動で進みます。生成された強みと課題案は、講師の確認後に本人へ届きます。"
      : "解析は手動実行です。Codexに「caliboo-strength-run の実日報モードで待ちジョブを処理」と依頼してください。"}</Alert>}
    <Button onClick={() => void queue.reload()}>解析状況を更新</Button>
    {queue.error && <Alert severity="error">{queue.error}</Alert>}
    {queue.data?.jobs.map((job) => <Paper key={job.id} sx={{ p: 2 }}><Stack spacing={1}>
      <Typography>#{job.id} / ユーザー {job.userId} / {kinds[job.kind]}</Typography>
      <Typography>{job.status === "failed" ? "処理に失敗しました" : job.processing ? "解析中" : job.lastError ? "再試行待ち" : "解析待ち"}
        {job.attempts ? ` / 試行 ${job.attempts}回` : ""}</Typography>
      {job.lastError && <Typography>{errors[job.lastError] ?? "解析できませんでした。設定と入力資料を確認してください。"}</Typography>}
      {job.status === "failed" && <Button disabled={queue.busy}
        onClick={() => void queue.act(`/api/development/jobs/${job.id}/retry`, {})}>解析 #{job.id} を再試行</Button>}
    </Stack></Paper>)}
    {queue.data?.jobs.length === 0 && <Typography>処理待ちはありません。</Typography>}
  </Stack>;
}
