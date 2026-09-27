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
        gap: "5px",
        padding: { xs: "7px 8px", sm: "8px 12px" },
        whiteSpace: "nowrap",
        background: "var(--color-orange-100)",
        borderRadius: "12px",
      }}
    >
      <i className="ph-fill ph-fire" aria-hidden="true" style={{ fontSize: 18, color: "var(--color-orange-600)" }} />
      <Box
        component="span"
        sx={{ fontFamily: NUMERIC_FONT_FAMILY, fontWeight: 800, fontSize: 17, color: "var(--color-text)" }}
      >
        {days}
      </Box>
      <Box component="span" sx={{ fontWeight: 600, fontSize: 12, color: "var(--color-orange-600)" }}>
        日連続
      </Box>
    </Box>
  );
}
