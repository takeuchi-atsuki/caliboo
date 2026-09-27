import TextField from "@mui/material/TextField";
import { useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";
import type { AssignmentStatus, AssignmentSubmissionDetail } from "../../lib/types";

export interface AssignmentFeedbackFormProps {
  assignmentId: number;
  status: AssignmentStatus;
  submission: AssignmentSubmissionDetail | null;
  submitting: boolean;
  onSubmit: (comment: string, score?: number | null) => Promise<void>;
}

export function AssignmentFeedbackForm({
  assignmentId,
  status,
  submission,
  submitting,
  onSubmit,
}: AssignmentFeedbackFormProps) {
  const [score, setScore] = useState(submission?.score?.toString() ?? "");
  const [comment, setComment] = useState(submission?.feedbackComment ?? "");

  useEffect(() => {
    setComment(submission?.feedbackComment ?? "");
    setScore(submission?.score?.toString() ?? "");
  }, [assignmentId, submission?.feedbackComment, submission?.score]);

  if (status === "not_submitted") {
    return (
      <div>
        <div style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)", marginBottom: 10 }}>
          フィードバック
        </div>
        <div style={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>
          まだ回答が提出されていないため、フィードバックを入力できません。
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)", marginBottom: 10 }}>
        フィードバック
      </div>
      <TextField label="点数（任意・0〜100）" type="number" value={score} onChange={(e) => setScore(e.target.value)}
        slotProps={{ htmlInput: { min: 0, max: 100, step: 1 } }} />
      <Textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="回答へのコメントを記入してください"
      />
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
        <Button disabled={submitting || comment.trim() === "" || (score !== "" && (!Number.isInteger(Number(score)) || Number(score) < 0 || Number(score) > 100))} onClick={() => onSubmit(comment, score === "" ? null : Number(score))}>
          {status === "reviewed" ? "フィードバックを更新する" : "フィードバックを送る"}
        </Button>
      </div>
    </div>
  );
}
