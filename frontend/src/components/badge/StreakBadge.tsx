import Box from "@mui/material/Box";

import { NUMERIC_FONT_FAMILY } from "../../theme";

export interface StreakBadgeProps {
  days: number;
}

export function StreakBadge({ days }: StreakBadgeProps) {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: "9px",
        padding: "9px 16px",
        background: "var(--color-bg)",
        borderRadius: "16px",
        boxShadow: "0 4px 14px color-mix(in srgb, var(--color-text) 5%, transparent)",
      }}
    >
      <i className="ph-fill ph-fire" style={{ fontSize: 20, color: "var(--color-orange-400)" }} />
      <Box
        component="span"
        sx={{ fontFamily: NUMERIC_FONT_FAMILY, fontWeight: 800, fontSize: 17, color: "var(--color-text)" }}
      >
        {days}
      </Box>
      <Box component="span" sx={{ fontWeight: 600, fontSize: 12, color: "var(--color-text-sub)" }}>
        日連続
      </Box>
    </Box>
  );
}
