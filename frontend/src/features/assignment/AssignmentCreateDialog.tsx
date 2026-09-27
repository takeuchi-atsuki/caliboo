import { MenuItem, TextField } from "@mui/material";
import { useResource } from "../../lib/useResource";
import type { ManagedUser } from "../../lib/types";
import { useState } from "react";

import { Dialog } from "../../components/ui/Dialog";
import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";

export interface AssignmentCreateDialogProps {
  open: boolean;
  onClose: () => void;
  submitting: boolean;
  onCreate: (title: string, body: string, targetUserId?: number) => Promise<boolean>;
}

export function AssignmentCreateDialog({ open, onClose, submitting, onCreate }: AssignmentCreateDialogProps) {
  const members = useResource<{ users: ManagedUser[] }>(open ? "/api/users" : null);
  const [target, setTarget] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  const canSubmit = title.trim() !== "" && body.trim() !== "" && !submitting;

  const handleCreate = async () => {
    const created = await onCreate(title, body, target ? Number(target) : undefined);
    if (created) {
      setTitle("");
      setBody("");
      setTarget("");
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="課題を作成">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <TextField select label="配信先" value={target} onChange={(e) => setTarget(e.target.value)}>
          <MenuItem value="">全員</MenuItem>
          {members.data?.users.filter((user) => user.role === "member" && user.active).map((user) =>
            <MenuItem key={user.id} value={String(user.id)}>{user.displayName}</MenuItem>)}
        </TextField>
        <div>
          <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text-sub)", marginBottom: 6 }}>
            タイトル
          </div>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="例: ビジネスメールの書き方をまとめよう"
            style={{
              width: "100%",
              boxSizing: "border-box",
              border: "1.5px solid var(--color-border)",
              background: "var(--color-bg)",
              borderRadius: 13,
              padding: "10px 13px",
              font: "500 13px/1.6 'M PLUS Rounded 1c'",
              color: "var(--color-text)",
            }}
          />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text-sub)", marginBottom: 6 }}>
            課題文
          </div>
          <Textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="課題の内容を記入してください" />
        </div>
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <Button disabled={!canSubmit} onClick={handleCreate}>
            作成する
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
