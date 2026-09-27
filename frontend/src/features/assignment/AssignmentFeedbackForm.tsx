import { useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";
import type { AssignmentStatus, AssignmentSubmissionDetail } from "../../lib/types";

export interface AssignmentFeedbackFormProps {
  assignmentId: number;
  status: AssignmentStatus;
  submission: AssignmentSubmissionDetail | null;
  submitting: boolean;
  onSubmit: (comment: string) => Promise<void>;
}

export function AssignmentFeedbackForm({
  assignmentId,
  status,
  submission,
  submitting,
  onSubmit,
}: AssignmentFeedbackFormProps) {
  const [comment, setComment] = useState(submission?.feedbackComment ?? "");

  useEffect(() => {
    setComment(submission?.feedbackComment ?? "");
  }, [assignmentId, submission?.feedbackComment]);

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
      <Textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="回答へのコメントを記入してください"
      />
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
        <Button disabled={submitting || comment.trim() === ""} onClick={() => onSubmit(comment)}>
          {status === "reviewed" ? "フィードバックを更新する" : "フィードバックを送る"}
        </Button>
      </div>
    </div>
  );
}
