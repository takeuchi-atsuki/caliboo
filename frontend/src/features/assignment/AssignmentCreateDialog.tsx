import { useState } from "react";

import { Dialog } from "../../components/ui/Dialog";
import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";

export interface AssignmentCreateDialogProps {
  open: boolean;
  onClose: () => void;
  submitting: boolean;
  onCreate: (title: string, body: string) => Promise<boolean>;
}

export function AssignmentCreateDialog({ open, onClose, submitting, onCreate }: AssignmentCreateDialogProps) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  const canSubmit = title.trim() !== "" && body.trim() !== "" && !submitting;

  const handleCreate = async () => {
    const created = await onCreate(title, body);
    if (created) {
      setTitle("");
      setBody("");
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="課題を作成">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
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
