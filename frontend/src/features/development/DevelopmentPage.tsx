import { useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { PageContainer } from "../../components/layout/PageContainer";
import { useAuth } from "../../components/auth/AuthProvider";
import { useResource } from "../../lib/useResource";
import type { AgentJob, ManagedUser, StrengthCandidate } from "../../lib/types";
import { LearningActions } from "./LearningActions";

export function DevelopmentPage() {
  const { user } = useAuth();
  const [target, setTarget] = useState("");
  const members = useResource<{ users: ManagedUser[] }>(user?.role === "admin" ? "/api/users" : null);
  const resource = useResource<{ candidates: StrengthCandidate[]; jobs: AgentJob[]; reviewPending?: boolean }>(
    `/api/development/strengths${target ? `?userId=${target}` : ""}`, 5000);
  return <PageContainer><Stack spacing={2} sx={{ p: { xs: 2, md: 4 } }}>
    <Typography component="h1" variant="h5">強みと成長のヒント</Typography>
    <Typography variant="body2">表示中は5秒ごとに更新します。講師が確認した強みを、次の行動に活かしましょう。</Typography>
    {resource.error && <Alert severity="error">{resource.error}</Alert>}
    <Button onClick={() => void resource.reload()}>更新する</Button>
    {user?.role === "admin" && <>
      <TextField select label="対象者" value={target} onChange={(e) => setTarget(e.target.value)}>
        <MenuItem value="">対象者を選択</MenuItem>
        {members.data?.users.filter((item) => item.role === "member" && item.active).map((item) =>
          <MenuItem key={item.id} value={String(item.id)}>{item.displayName}</MenuItem>)}
      </TextField>
      <Button disabled={!target || resource.busy} onClick={() => void resource.act(`/api/development/strengths/${target}/request`, {})}>強みの解析を依頼</Button>
      <Typography variant="body2">提出済みの日報・課題を解析対象にします。解析後、候補を確認して承認してください。</Typography>
      <Link to="/strengths/poc">解析PoCと比較結果</Link>
    </>}
    {resource.data?.jobs.some((job) => job.status === "pending") && <Alert severity="info">解析待ちです。結果の到着後に講師が確認します。</Alert>}
    {resource.data?.jobs.some((job) => job.status === "failed") && <Alert severity="warning">解析を完了できませんでした。講師が状況を確認できます。提出した内容は保存されています。</Alert>}
    {resource.data?.reviewPending && user?.role !== "admin" && <Alert severity="info">解析結果を講師が確認しています。承認後にここへ届きます。</Alert>}
    {resource.data?.candidates.length === 0 && <Typography>表示できる強みはまだありません。日報や課題の取り組みが材料になります。</Typography>}
    {resource.data?.candidates.map((candidate) => <Candidate key={candidate.id} candidate={candidate}
      admin={user?.role === "admin"} busy={resource.busy} decide={(body) => resource.act(`/api/development/strengths/${candidate.id}/decision`, body)} />)}
    <LearningActions key={target} target={target} admin={user?.role === "admin"} candidates={resource.data?.candidates ?? []} />
  </Stack></PageContainer>;
}

function Candidate({ candidate, admin, busy, decide }: {
  candidate: StrengthCandidate; admin: boolean; busy: boolean; decide: (body: unknown) => Promise<boolean>;
}) {
  const [label, setLabel] = useState(candidate.label);
  const [growthAction, setGrowthAction] = useState(candidate.growthAction);
  const pending = admin && candidate.status === "pending";
  const labels: Record<string, string> = { pending: "確認待ち", approved: "承認済み", rejected: "見送り", superseded: "更新済み" };
  return <Paper sx={{ p: 2 }}><Stack spacing={2}>
    <Typography component="h2" variant="h6">{candidate.label}</Typography>
    {admin && <Typography>{labels[candidate.status]} / 確信度 {candidate.confidence}%</Typography>}
    {candidate.evidence.map((item, index) => <Typography key={index} component="blockquote" sx={{ m: 0, pl: 2, borderLeft: "3px solid", borderColor: "divider" }}>
      {item.quote}<br /><small>{item.source.date} / {item.materialId}</small>
    </Typography>)}
    {pending ? <><TextField label="強みの表現" value={label} onChange={(e) => setLabel(e.target.value)} />
      <TextField label="次の取り組み" multiline value={growthAction} onChange={(e) => setGrowthAction(e.target.value)} />
      <Stack direction="row" spacing={1}><Button disabled={busy || !label.trim() || !growthAction.trim()}
        onClick={() => void decide({ status: "approved", label, growthAction })}>承認して表示</Button>
        <Button disabled={busy} onClick={() => void decide({ status: "rejected", label: candidate.label, growthAction: candidate.growthAction })}>見送る</Button></Stack>
    </> : <Typography>次の取り組み: {candidate.growthAction}</Typography>}
  </Stack></Paper>;
}
