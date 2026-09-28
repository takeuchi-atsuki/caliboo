import { useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useResource } from "../../lib/useResource";
import type { AssignmentListItem, LearningAction, StrengthCandidate } from "../../lib/types";

const statuses = { planned: "予定", in_progress: "取り組み中", completed: "完了", cancelled: "見送り" };
const assignmentStatuses = { not_submitted: "未提出", submitted: "レビュー待ち", reviewed: "フィードバック済み" };
type Save = (path: string, body: unknown) => Promise<boolean>;

export function LearningActions({ target, admin, candidates }: {
  target: string; admin: boolean; candidates: StrengthCandidate[];
}) {
  const resource = useResource<{ actions: LearningAction[]; assignments: AssignmentListItem[] }>(
    admin && !target ? null : `/api/development/actions${target ? `?userId=${target}` : ""}`, 5000);
  if (admin && !target) return null;
  return <Stack spacing={2}>
    <Typography component="h2" variant="h6">自分で決める次の一歩</Typography>
    {resource.error && <Alert severity="error">{resource.error}</Alert>}
    {!admin && <ActionCreate candidates={candidates} busy={resource.busy} save={resource.act} />}
    {resource.data?.actions.length === 0 && <Typography>小さな行動から決めてみましょう。</Typography>}
    {resource.data?.actions.map((action) => <ActionCard key={action.id} action={action}
      admin={admin} busy={resource.busy} save={resource.act} />)}
    <Typography component="h2" variant="h6">配信された課題</Typography>
    {resource.data?.assignments.map((assignment) => <Paper key={assignment.id} sx={{ p: 2 }}>
      <Link to={`/assignment/${assignment.id}`}>{assignment.title}</Link>
      <Typography variant="body2">{assignmentStatuses[assignment.status]}{assignment.target ? " / 個人向け" : ""}</Typography>
    </Paper>)}
    {resource.data?.assignments.length === 0 && <Typography>配信された課題はありません。</Typography>}
  </Stack>;
}

function ActionCreate({ candidates, busy, save }: { candidates: StrengthCandidate[]; busy: boolean; save: Save }) {
  const [title, setTitle] = useState("");
  const [criteria, setCriteria] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [candidateId, setCandidateId] = useState("");
  const [notice, setNotice] = useState("");
  const approved = candidates.filter((candidate) => candidate.status === "approved");
  const submit = async () => {
    if (await save("/api/development/actions", { title, successCriteria: criteria,
      dueDate: dueDate || null, candidateId: candidateId ? Number(candidateId) : null })) {
      setTitle(""); setCriteria(""); setDueDate(""); setCandidateId(""); setNotice("次の一歩を保存しました。");
    }
  };
  return <Paper component="form" onSubmit={(event) => { event.preventDefault(); void submit(); }} sx={{ p: 2 }}>
    <Stack spacing={2}>
      <Typography>強みのヒントを参考に、取り組む内容と達成の目安を自分で決めましょう。</Typography>
      {notice && <Alert severity="success">{notice}</Alert>}
      <TextField select label="参考にする強み（任意）" value={candidateId} disabled={busy}
        onChange={(event) => {
          const selected = event.target.value;
          setCandidateId(selected);
          const candidate = approved.find((item) => String(item.id) === selected);
          if (candidate) setTitle(candidate.growthAction.slice(0, 1000));
        }}>
        <MenuItem value="">自分で入力する</MenuItem>
        {approved.map((candidate) => <MenuItem key={candidate.id} value={String(candidate.id)}>{candidate.label}</MenuItem>)}
        {candidateId && !approved.some((item) => String(item.id) === candidateId) &&
          <MenuItem value={candidateId}>強みが更新されました。選び直してください</MenuItem>}
      </TextField>
      <TextField label="次に取り組むこと" required multiline value={title} disabled={busy}
        onChange={(event) => setTitle(event.target.value)} slotProps={{ htmlInput: { maxLength: 1000 } }} />
      <TextField label="達成の目安" required multiline value={criteria} disabled={busy}
        onChange={(event) => setCriteria(event.target.value)} slotProps={{ htmlInput: { maxLength: 1000 } }} />
      <TextField label="期限（任意）" type="date" value={dueDate} disabled={busy}
        onChange={(event) => setDueDate(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} />
      <Button type="submit" disabled={busy || !title.trim() || !criteria.trim()}>この行動を始める</Button>
    </Stack>
  </Paper>;
}

function ActionCard({ action, admin, busy, save }: {
  action: LearningAction; admin: boolean; busy: boolean; save: Save;
}) {
  const [editing, setEditing] = useState(false);
  return <Paper sx={{ p: 2 }}><Stack spacing={1}>
    <Typography component="h3" variant="subtitle1">{action.title}</Typography>
    <Typography>{statuses[action.status]}{action.dueDate ? ` / 期限 ${action.dueDate}` : ""}</Typography>
    <Typography>達成の目安: {action.successCriteria}</Typography>
    {action.strengthSnapshot && <Typography>参考にした強み: {action.strengthSnapshot.label}</Typography>}
    {action.reflection && <Typography>振り返り: {action.reflection}</Typography>}
    {!admin && !editing && <Button onClick={() => setEditing(true)}>行動を編集・振り返る</Button>}
    {editing && <ActionEditor action={action} busy={busy} save={save} close={() => setEditing(false)} />}
  </Stack></Paper>;
}

function ActionEditor({ action, busy, save, close }: {
  action: LearningAction; busy: boolean; save: Save; close: () => void;
}) {
  // !NOTE: 自動取得では入力と版番号を置換しない。別画面の編集とは409で競合を検出する。
  const [draft, setDraft] = useState(action);
  const changedElsewhere = draft.revision !== action.revision;
  const submit = async () => {
    if (await save(`/api/development/actions/${action.id}`, draft)) close();
  };
  return <Stack component="form" spacing={2} onSubmit={(event) => { event.preventDefault(); void submit(); }}>
    {changedElsewhere && <Alert severity="warning">別の画面で更新されました。入力を控え、閉じてから編集し直してください。</Alert>}
    <TextField label="行動の内容" value={draft.title} disabled={busy} required multiline
      onChange={(event) => setDraft({ ...draft, title: event.target.value })} slotProps={{ htmlInput: { maxLength: 1000 } }} />
    <TextField label="達成の目安を編集" value={draft.successCriteria} disabled={busy} required multiline
      onChange={(event) => setDraft({ ...draft, successCriteria: event.target.value })} slotProps={{ htmlInput: { maxLength: 1000 } }} />
    <TextField label="期限を編集" type="date" value={draft.dueDate ?? ""} disabled={busy}
      onChange={(event) => setDraft({ ...draft, dueDate: event.target.value || null })} slotProps={{ inputLabel: { shrink: true } }} />
    <TextField select label="取り組み状況" value={draft.status} disabled={busy}
      onChange={(event) => setDraft({ ...draft, status: event.target.value as LearningAction["status"] })}>
      {Object.entries(statuses).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
    </TextField>
    <TextField label="振り返り" multiline value={draft.reflection} disabled={busy} required={draft.status === "completed"}
      helperText="完了するときは、実践して分かったことを記録しましょう。"
      onChange={(event) => setDraft({ ...draft, reflection: event.target.value })} slotProps={{ htmlInput: { maxLength: 5000 } }} />
    <Button type="submit" disabled={busy || changedElsewhere || !draft.title.trim() || !draft.successCriteria.trim() ||
      (draft.status === "completed" && !draft.reflection.trim())}>変更を保存</Button>
    <Button disabled={busy} onClick={close}>編集を閉じる</Button>
  </Stack>;
}
