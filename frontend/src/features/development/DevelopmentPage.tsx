import { useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Box, Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { PageContainer } from "../../components/layout/PageContainer";
import { useAuth } from "../../components/auth/AuthProvider";
import { useResource } from "../../lib/useResource";
import type { AgentJob, ManagedUser, StrengthCandidate, StrengthKind } from "../../lib/types";
import { LearningActions } from "./LearningActions";

const strengthGroups: { kind: StrengthKind; title: string; empty: string }[] = [
  { kind: "ability", title: "得意な能力", empty: "表示できる能力はまだありません。" },
  { kind: "work_style", title: "性格・仕事の進め方の傾向", empty: "表示できる仕事の傾向はまだありません。" },
];

export function DevelopmentPage() {
  const { user } = useAuth();
  const [target, setTarget] = useState("");
  const members = useResource<{ users: ManagedUser[] }>(user?.role === "admin" ? "/api/users" : null);
  const resource = useResource<{ candidates: StrengthCandidate[]; jobs: AgentJob[]; reviewPending?: boolean }>(
    `/api/development/strengths${target ? `?userId=${target}` : ""}`, 5000);
  const candidates = resource.data?.candidates;
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
    {candidates && strengthGroups.map((group) => {
      // !NOTE: kindのない旧候補は能力として扱い、旧データも本人の強み画面から消さない。
      const groupCandidates = candidates.filter((candidate) => (candidate.kind ?? "ability") === group.kind);
      return <Box component="section" key={group.kind} aria-label={group.title}>
        <Typography component="h2" variant="h6" sx={{ mb: 2 }}>{group.title}</Typography>
        <Stack spacing={2}>
          {groupCandidates.length === 0 && <Typography color="text.secondary">{group.empty}日報や課題の取り組みが材料になります。</Typography>}
          {groupCandidates.map((candidate) => <Candidate key={candidate.id} candidate={candidate}
            admin={user?.role === "admin"} busy={resource.busy} decide={(body) => resource.act(`/api/development/strengths/${candidate.id}/decision`, body)} />)}
        </Stack>
      </Box>;
    })}
    <LearningActions key={target} target={target} admin={user?.role === "admin"} candidates={candidates ?? []} />
  </Stack></PageContainer>;
}

function Candidate({ candidate, admin, busy, decide }: {
  candidate: StrengthCandidate; admin: boolean; busy: boolean; decide: (body: unknown) => Promise<boolean>;
}) {
  const [label, setLabel] = useState(candidate.label);
  const [summary, setSummary] = useState(candidate.summary ?? "");
  const [scopeNote, setScopeNote] = useState(candidate.scopeNote ?? "");
  const [growthAction, setGrowthAction] = useState(candidate.growthAction);
  const pending = admin && candidate.status === "pending";
  const labels: Record<string, string> = { pending: "確認待ち", approved: "承認済み", rejected: "見送り", superseded: "更新済み" };
  return <Paper sx={{ p: 2 }}><Stack spacing={2}>
    <Typography component="h3" variant="h6">{candidate.label}</Typography>
    {candidate.summary && <Typography>{candidate.summary}</Typography>}
    {admin && <Typography>{labels[candidate.status]} / 確信度 {candidate.confidence}%</Typography>}
    {candidate.scopeNote && <Typography variant="body2" color="text.secondary">評価できる範囲: {candidate.scopeNote}</Typography>}
    {!pending && <Typography>次の取り組み: {candidate.growthAction}</Typography>}
    <Box component="details" sx={{ '& summary': { cursor: "pointer", fontWeight: 700 } }}>
      <Box component="summary">根拠を見る（{candidate.evidence.length}件）</Box>
      <Stack spacing={1} sx={{ mt: 1 }}>
        {candidate.evidence.map((item, index) => <Typography key={index} component="blockquote" sx={{ m: 0, pl: 2, borderLeft: "3px solid", borderColor: "divider", overflowWrap: "anywhere" }}>
          {item.quote}<br /><small>{item.source.date} / {item.source.field} / {item.materialId}</small>
        </Typography>)}
        {candidate.evidence.length === 0 && <Typography variant="body2">引用できる根拠はありません。</Typography>}
        <Typography variant="caption" color="text.secondary">スキルコード: {candidate.skillCode}</Typography>
      </Stack>
    </Box>
    {pending ? <><TextField label="強みの表現" value={label} onChange={(e) => setLabel(e.target.value)} />
      <TextField label="強みの解釈" multiline value={summary} onChange={(e) => setSummary(e.target.value)} />
      <TextField label="評価できる範囲" multiline value={scopeNote} onChange={(e) => setScopeNote(e.target.value)} />
      <TextField label="次の取り組み" multiline value={growthAction} onChange={(e) => setGrowthAction(e.target.value)} />
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}><Button disabled={busy || !label.trim() || !growthAction.trim() || (candidate.kind === "work_style" && (!summary.trim() || !scopeNote.trim()))}
        onClick={() => void decide({ status: "approved", label: label.trim(), summary: summary.trim(), scopeNote: scopeNote.trim(), growthAction: growthAction.trim() })}>承認して表示</Button>
        <Button disabled={busy} onClick={() => void decide({ status: "rejected", label: candidate.label, growthAction: candidate.growthAction })}>見送る</Button></Stack>
    </> : null}
  </Stack></Paper>;
}
