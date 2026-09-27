import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Alert, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { PageContainer } from "../../components/layout/PageContainer";
import { useAuth } from "../../components/auth/AuthProvider";
import { useResource } from "../../lib/useResource";
import type { AgentJob } from "../../lib/types";

interface Evaluation { evaluatedJobs: number; requiredJobs: number; agreement: number; acceptance: number; status: string }
export function AgentJobsPage() {
  const { user } = useAuth();
  const enabled = user?.role === "admin";
  const queue = useResource<{ jobs: AgentJob[] }>(enabled ? "/api/development/jobs" : null);
  const evaluation = useResource<Evaluation>(enabled ? "/api/development/evaluations" : null);
  if (!enabled) return <Navigate to="/home" replace />;
  return <PageContainer><Stack spacing={2} sx={{ p: 3 }}>
    <Typography component="h1" variant="h5">解析管理</Typography>
    <Alert severity="info">Codexで「caliboo-strength-run の実日報モードで待ちジョブを処理」と依頼してください。APIキーは不要です。</Alert>
    <Button onClick={() => { void queue.reload(); void evaluation.reload(); }}>更新する</Button>
    {queue.error && <Alert severity="error">{queue.error}</Alert>}
    {queue.data?.jobs.map((job) => <Paper key={job.id} sx={{ p: 2 }}>
      #{job.id} / ユーザー {job.userId} / {job.kind === "strength" ? "強み解析" : "課題案の再生成"} / 解析待ち
    </Paper>)}
    {queue.data?.jobs.length === 0 && <Typography>処理待ちはありません。</Typography>}
    <Typography component="h2" variant="h6">実日報による妥当性評価</Typography>
    <Typography>目安: 20件・各2名、部分一致以上80%・受容80%。独立した人間ラベルを入力します。</Typography>
    {evaluation.data && <Alert severity={evaluation.data.status === "passed" ? "success" : "info"}>
      {evaluation.data.status === "insufficient_data" ? "評価データ不足" : evaluation.data.status === "passed" ? "目安達成" : "目安未達"}:
      {evaluation.data.evaluatedJobs}/{evaluation.data.requiredJobs}件、一致 {Math.round(evaluation.data.agreement * 100)}%、受容 {Math.round(evaluation.data.acceptance * 100)}%
    </Alert>}
    <EvaluationForm busy={evaluation.busy} save={evaluation.act} />
    {evaluation.error && <Alert severity="error">{evaluation.error}</Alert>}
  </Stack></PageContainer>;
}
function EvaluationForm({ busy, save }: { busy: boolean; save: (path: string, body: unknown) => Promise<boolean> }) {
  const [jobId, setJobId] = useState("");
  const [skillCodes, setSkillCodes] = useState("");
  const [comment, setComment] = useState("");
  const materials = useResource<{ materials: { sources: { id: string; text: string }[] } }>(jobId ? `/api/development/evaluations/${jobId}/materials` : null);
  return <Stack spacing={2}>
    <TextField label="評価する解析番号" type="number" value={jobId} onChange={(e) => setJobId(e.target.value)} />
    {materials.data?.materials.sources.map((source) => <Typography key={source.id}>{source.id}: {source.text}</Typography>)}
    {materials.error && <Alert severity="error">{materials.error}</Alert>}
    <TextField label="人間が判断したスキルコード（カンマ区切り、該当なしは空欄）" value={skillCodes} onChange={(e) => setSkillCodes(e.target.value)} />
    <TextField label="評価コメント" multiline value={comment} onChange={(e) => setComment(e.target.value)} />
    <Stack direction="row" spacing={1}>{[true, false].map((accepted) => <Button key={String(accepted)} disabled={busy || !jobId || !comment.trim()}
      onClick={() => void save(`/api/development/evaluations/${jobId}`, { skillCodes: skillCodes.split(",").map((code) => code.trim()).filter(Boolean), accepted, comment })}>
      {accepted ? "受容して記録" : "改善が必要として記録"}</Button>)}</Stack>
  </Stack>;
}
