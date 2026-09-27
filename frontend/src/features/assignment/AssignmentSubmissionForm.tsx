import { useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";
import type { AssignmentDetail } from "../../lib/types";

export interface AssignmentSubmissionFormProps {
  assignment: AssignmentDetail;
  submitting: boolean;
  onSubmit: (answerText: string) => Promise<void>;
}

export function ReadOnlyAnswer({ text }: { text: string }) {
  return (
    <div
      style={{
        whiteSpace: "pre-wrap",
        border: "1.5px solid var(--color-border)",
        background: "var(--color-bg)",
        borderRadius: 13,
        padding: 13,
        font: "500 13px/1.6 'M PLUS Rounded 1c'",
        color: "var(--color-text)",
      }}
    >
      {text}
    </div>
  );
}

export function AssignmentSubmissionForm({ assignment, submitting, onSubmit }: AssignmentSubmissionFormProps) {
  const [answerText, setAnswerText] = useState(assignment.submission?.answerText ?? "");

  useEffect(() => {
    setAnswerText(assignment.submission?.answerText ?? "");
  }, [assignment.id, assignment.submission?.answerText]);

  const heading = "あなたの回答";

  if (assignment.status === "reviewed") {
    return (
      <div>
        <div style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)", marginBottom: 10 }}>{heading}</div>
        <ReadOnlyAnswer text={assignment.submission?.answerText ?? ""} />
      </div>
    );
  }

  return (
    <div>
      <div style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)", marginBottom: 10 }}>{heading}</div>
      <Textarea
        value={answerText}
        onChange={(e) => setAnswerText(e.target.value)}
        placeholder="ここに回答を記入してください"
      />
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
        <Button
          icon="ph-bold ph-paper-plane-tilt"
          disabled={submitting || answerText.trim() === ""}
          onClick={() => onSubmit(answerText)}
        >
          {assignment.status === "submitted" ? "再提出する" : "提出する"}
        </Button>
      </div>
    </div>
  );
}
