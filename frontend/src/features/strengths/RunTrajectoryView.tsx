import Box from "@mui/material/Box";

import { Tag } from "../../components/badge/Tag";
import type { PocRunDetail } from "../../lib/types";

export interface RunTrajectoryViewProps {
  detail: PocRunDetail;
}

/** 3周の軌跡・日報・レビューを、解析の入力として辿れる形で並べる。 */
export function RunTrajectoryView({ detail }: RunTrajectoryViewProps) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <Box sx={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)" }}>解析のもとになった記録</Box>

      <Box
        sx={{
          background: "var(--color-panel)",
          borderRadius: "20px",
          padding: "18px 22px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        <Box sx={{ fontWeight: 700, fontSize: 13, color: "var(--color-text-sub2)" }}>
          ① 3周のループ（タスク → 実行 → フィードバック）
        </Box>
        {detail.trajectory.map((iteration) => (
          <Box
            key={iteration.iteration}
            sx={{
              paddingLeft: "14px",
              borderLeft: "3px solid var(--color-purple-200)",
              display: "flex",
              flexDirection: "column",
              gap: "6px",
            }}
          >
            <Box sx={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              <Tag label={`${iteration.iteration}周目`} tone="purple" />
              <Box component="span" sx={{ fontWeight: 800, fontSize: 13.5, color: "var(--color-text)" }}>
                {iteration.task.title}
              </Box>
            </Box>
            <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text)" }}>
              <strong>成果物：</strong>
              {iteration.workerOutput}
            </Box>
            <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>
              <strong>フィードバック：</strong>
              {iteration.trainerFeedback}
            </Box>
          </Box>
        ))}
      </Box>

      <Box
        sx={{
          background: "var(--color-panel)",
          borderRadius: "20px",
          padding: "18px 22px",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        <Box sx={{ fontWeight: 700, fontSize: 13, color: "var(--color-text-sub2)" }}>
          ② 日報（{detail.diary.date}）
        </Box>
        {detail.diary.tasks.map((task, index) => (
          <Box key={index} sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text)" }}>
            {task.time}　{task.what}（{task.progressRate}％）／ {task.progressDesc}
          </Box>
        ))}
        <Box sx={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "4px" }}>
          <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text)" }}>
            <strong>Keep：</strong>
            {detail.diary.kpt.keep}
          </Box>
          <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text)" }}>
            <strong>Problem：</strong>
            {detail.diary.kpt.problem}
          </Box>
          <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text)" }}>
            <strong>Try：</strong>
            {detail.diary.kpt.try}
          </Box>
          <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>
            <strong>きもち：</strong>
            {detail.diary.feelings.emotion}（{detail.diary.feelings.trigger}）
          </Box>
        </Box>
      </Box>

      <Box
        sx={{
          background: "var(--color-panel)",
          borderRadius: "20px",
          padding: "18px 22px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        <Box sx={{ fontWeight: 700, fontSize: 13, color: "var(--color-text-sub2)" }}>
          ③ 3職種レビューと統合結果
        </Box>
        {detail.reviews.reviews.map((review) => (
          <Box key={review.agentKey} sx={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <Box sx={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              <Box component="span" sx={{ fontWeight: 800, fontSize: 13, color: "var(--color-text)" }}>
                {review.reviewerRole}
              </Box>
              <Tag label={review.magiTone} tone="blue" />
            </Box>
            <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>{review.comment}</Box>
          </Box>
        ))}
        {detail.reviews.fanInFlags.length > 0 ? (
          <Box sx={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {detail.reviews.fanInFlags.map((flag) => (
              <Tag key={flag} label={flag} tone="orange" />
            ))}
          </Box>
        ) : null}
      </Box>
    </Box>
  );
}
