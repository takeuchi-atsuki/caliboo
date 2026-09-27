import { useState } from "react";
import { Alert, Button, Stack, TextField, Typography } from "@mui/material";
import { useResource } from "../../lib/useResource";

export function ProposalRegenerate({ proposalId, pending, generator }: { proposalId: number; pending: boolean; generator: string }) {
  const [instruction, setInstruction] = useState("");
  const [requested, setRequested] = useState(false);
  const revisions = useResource<{ revisions: { id: number; instruction: string; previous: { title: string; body: string } }[] }>(`/api/assignment-proposals/${proposalId}/revisions`);
  return <Stack spacing={2}>
    <Typography variant="body2">生成元: {generator.startsWith("codex_agent") ? "エージェント" : "ルールベース"}</Typography>
    {pending && <><TextField label="AIに調整を頼む" multiline value={instruction} onChange={(e) => setInstruction(e.target.value)} />
      <Button disabled={revisions.busy || !instruction.trim()} onClick={async () => {
        if (await revisions.act(`/api/assignment-proposals/${proposalId}/regenerate`, { instruction })) setRequested(true);
      }}>作り直しを依頼</Button></>}
    {requested && <Alert severity="info">再生成を依頼しました。解析管理で処理後、このページを再読み込みしてください。</Alert>}
    {revisions.error && <Alert severity="error">{revisions.error}</Alert>}
    {revisions.data?.revisions.map((revision) => <details key={revision.id}><summary>調整履歴: {revision.instruction}</summary>
      <Typography>{revision.previous.title}</Typography><Typography sx={{ whiteSpace: "pre-wrap" }}>{revision.previous.body}</Typography>
    </details>)}
  </Stack>;
}
