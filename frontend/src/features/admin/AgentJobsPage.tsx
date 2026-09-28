import { Navigate } from "react-router-dom";
import { Alert, Button, Stack, Typography } from "@mui/material";
import { PageContainer } from "../../components/layout/PageContainer";
import { useAuth } from "../../components/auth/AuthProvider";
import { useResource } from "../../lib/useResource";
import { AgentJobQueue } from "./AgentJobQueue";
import { HoldoutEvaluation } from "./HoldoutEvaluation";

interface Evaluation { evaluatedJobs: number; requiredJobs: number; agreement: number; acceptance: number; status: string; legacyEvaluations: number; trace: { provider: string; model: string; promptVersion: string } | null }
export function AgentJobsPage() {
  const { user } = useAuth();
  const enabled = user?.role === "admin";
  const evaluation = useResource<Evaluation>(enabled ? "/api/development/evaluations" : null);
  if (!enabled) return <Navigate to="/home" replace />;
  return <PageContainer><Stack spacing={2} sx={{ p: 3 }}>
    <Typography component="h1" variant="h5">解析管理</Typography>
    <AgentJobQueue enabled={enabled} />
    <Button onClick={() => void evaluation.reload()}>評価を更新する</Button>
    <Typography component="h2" variant="h6">実日報による妥当性評価</Typography>
    <Typography>目安: 20件・各2名、部分一致以上80%・受容80%。独立した人間ラベルを入力します。</Typography>
    {evaluation.data && <Alert severity={evaluation.data.status === "passed" ? "success" : "info"}>
      {evaluation.data.status === "insufficient_data" ? "評価データ不足" : evaluation.data.status === "passed" ? "目安達成" : "目安未達"}:
      {evaluation.data.evaluatedJobs}/{evaluation.data.requiredJobs}件、一致 {Math.round(evaluation.data.agreement * 100)}%、受容 {Math.round(evaluation.data.acceptance * 100)}%
    </Alert>}
    {evaluation.data?.trace && <Typography>評価対象: {evaluation.data.trace.provider} / {evaluation.data.trace.model} / {evaluation.data.trace.promptVersion}</Typography>}
    <Typography>旧方式の参考評価: {evaluation.data?.legacyEvaluations ?? 0}件（合格判定には含めません）</Typography>
    <HoldoutEvaluation reviewerId={user.id} />
    {evaluation.error && <Alert severity="error">{evaluation.error}</Alert>}
  </Stack></PageContainer>;
}
