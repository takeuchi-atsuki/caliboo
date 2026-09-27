import Box from "@mui/material/Box";
import CardActionArea from "@mui/material/CardActionArea";
import { useTheme } from "@mui/material/styles";

import { DonutProgress } from "../../components/progress/DonutProgress";
import { PhosphorIcon } from "../../components/icon/PhosphorIcon";
import { Tag } from "../../components/badge/Tag";
import {
  confidencePercent,
  learningDeltaIcon,
  learningDeltaLabel,
  strengthStatusLabel,
  strengthStatusTone,
} from "../../lib/strengthStatus";
import type { StrengthItem } from "../../lib/types";

export interface StrengthCardProps {
  strength: StrengthItem;
  onOpenEvidence: (strength: StrengthItem) => void;
}

export function StrengthCard({ strength, onOpenEvidence }: StrengthCardProps) {
  const theme = useTheme();
  const tone = strengthStatusTone(strength.status);
  const accent = theme.palette.accent[tone];
  const held = strength.status === "insufficient_evidence";

  return (
    <CardActionArea
      onClick={() => onOpenEvidence(strength)}
      sx={{
        borderRadius: "20px",
        padding: "20px 22px",
        background: "var(--color-panel)",
        border: `1px solid ${held ? "var(--color-border-soft)" : accent.wash}`,
        opacity: held ? 0.78 : 1,
        display: "block",
        textAlign: "left",
      }}
    >
      <Box sx={{ display: "flex", gap: "18px", alignItems: "flex-start" }}>
        <DonutProgress
          percent={confidencePercent(strength.confidence)}
          size={92}
          color={accent.main}
          trackColor={accent.wash}
          label={`${confidencePercent(strength.confidence)}%`}
          subLabel="確信度"
        />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <Box component="span" sx={{ fontWeight: 800, fontSize: 16, color: "var(--color-text)" }}>
              {strength.layerTask.skillName}
            </Box>
            <Tag label={strengthStatusLabel(strength.status)} tone={tone} />
          </Box>
          <Box sx={{ fontWeight: 600, fontSize: 12, color: "var(--color-text-sub2)", marginTop: "4px" }}>
            SFIA {strength.layerTask.skillCode} ・ レベル{strength.layerTask.level}
          </Box>

          <Box sx={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "10px" }}>
            {strength.layerBehavior.themes.map((theme_) => (
              <Tag key={theme_} label={theme_} tone="purple" />
            ))}
          </Box>

          {strength.layerWillSkill ? (
            <Box sx={{ fontWeight: 700, fontSize: 12.5, color: accent.main, marginTop: "10px" }}>
              {strength.layerWillSkill.quadrant}
            </Box>
          ) : (
            <Box sx={{ fontWeight: 600, fontSize: 12, color: "var(--color-text-sub2)", marginTop: "10px" }}>
              根拠が足りないため、Will-Skill象限は判定していません
            </Box>
          )}

          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontWeight: 600,
              fontSize: 12,
              color: "var(--color-text-sub)",
              marginTop: "8px",
            }}
          >
            <PhosphorIcon name={learningDeltaIcon(strength.learningAgility.delta)} size={14} />
            {learningDeltaLabel(strength.learningAgility.delta)}：{strength.learningAgility.note}
          </Box>

          {strength.growthContent && strength.layerWillSkill ? (
            <Box
              sx={{
                marginTop: "12px",
                padding: "10px 12px",
                borderRadius: "12px",
                background: accent.wash,
              }}
            >
              <Box sx={{ fontWeight: 800, fontSize: 12, color: accent.main }}>
                次の一手：{strength.growthContent.title}
              </Box>
              <Box sx={{ fontWeight: 500, fontSize: 12, color: "var(--color-text-sub)", marginTop: "2px" }}>
                {strength.layerWillSkill.policy}
              </Box>
            </Box>
          ) : null}

          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: "5px",
              fontWeight: 700,
              fontSize: 12,
              color: "var(--color-text-sub)",
              marginTop: "12px",
            }}
          >
            <PhosphorIcon name="ph-bold ph-magnifying-glass" size={13} />
            根拠を見る（{strength.evidence.length}件）
          </Box>
        </Box>
      </Box>
    </CardActionArea>
  );
}
