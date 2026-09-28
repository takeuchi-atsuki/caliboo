import { Typography } from "@mui/material";
import type { QuizQuestion } from "../../lib/types";

const labels = {
  mistake_review: "誤答の復習：前に間違えた問題をもう一度考えてみましょう。",
  scheduled_review: "復習のタイミング：前に学んだ内容を確かめましょう。",
  new: "新しい問題：まずは自分で考えてみましょう。",
  practice: "練習：解き方を自分の言葉で説明してみましょう。",
};

export function QuizPracticeReason({ reason = "practice" }: { reason?: QuizQuestion["practiceReason"] }) {
  return <Typography sx={{ mb: 2, fontSize: 13, color: "text.secondary" }}>{labels[reason]}</Typography>;
}
