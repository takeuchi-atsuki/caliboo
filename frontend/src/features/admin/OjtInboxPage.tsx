import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useAuth } from "../../components/auth/AuthProvider";
import { PageContainer } from "../../components/layout/PageContainer";
import { useResource } from "../../lib/useResource";
import type { ChatMessage, Department } from "../../lib/types";

interface Thread { id: number; displayName: string; departmentName: string; departmentId: string; resolvedAt: string | null; messages: ChatMessage[] }
export function OjtInboxPage() {
  const { user } = useAuth();
  const resource = useResource<{ threads: Thread[]; pendingCount: number }>(user?.role === "admin" ? "/api/ojt/escalations" : null);
  const departments = useResource<{ departments: Department[] }>("/api/ojt/departments");
  const [filter, setFilter] = useState("");
  if (user?.role !== "admin") return <Navigate to="/home" replace />;
  return <PageContainer><Stack spacing={2} sx={{ p: 3 }}>
    <Typography variant="h5" component="h1">OJT相談（未回答 {resource.data?.pendingCount ?? 0}件）</Typography>
    <Button onClick={() => void resource.reload()}>更新する</Button>
    {resource.error && <Alert severity="error">{resource.error}</Alert>}
    <TextField select label="課で絞り込む" value={filter} onChange={(e) => setFilter(e.target.value)}>
      <MenuItem value="">すべて</MenuItem>
      {departments.data?.departments.map((dept) => <MenuItem key={dept.id} value={dept.id}>{dept.name}</MenuItem>)}
    </TextField>
    {resource.data?.threads.filter((thread) => !filter || thread.departmentId === filter).map((thread) =>
      <ThreadReply key={thread.id} thread={thread} busy={resource.busy} reply={(text) => resource.act(`/api/ojt/escalations/${thread.id}/reply`, { text })} />)}
    {resource.data?.threads.length === 0 && <Typography>相談はまだありません。</Typography>}
  </Stack></PageContainer>;
}
function ThreadReply({ thread, busy, reply }: { thread: Thread; busy: boolean; reply: (text: string) => Promise<boolean> }) {
  const [text, setText] = useState("");
  return <Paper sx={{ p: 2 }}><Stack spacing={2}>
    <Typography component="h2" variant="h6">{thread.displayName} / {thread.departmentName} {thread.resolvedAt ? "回答済み" : "回答待ち"}</Typography>
    {thread.messages.map((message) => <Typography key={message.id} sx={{ whiteSpace: "pre-wrap" }}>
      {message.role === "me" ? thread.displayName : "メンター"}: {message.text}
    </Typography>)}
    {!thread.resolvedAt && <><TextField label="回答" multiline value={text} onChange={(e) => setText(e.target.value)} />
      <Button disabled={busy || !text.trim()} onClick={() => void reply(text)}>回答を送る</Button></>}
  </Stack></Paper>;
}
