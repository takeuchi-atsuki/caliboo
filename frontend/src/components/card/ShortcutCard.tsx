import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

import type { Tone } from "../../lib/types";
import { PhosphorIcon } from "../icon/PhosphorIcon";

export interface ShortcutCardProps {
  icon: string;
  title: string;
  description?: string;
  tone: Tone;
  to: string;
}

export function ShortcutCard({ icon, title, description, tone, to }: ShortcutCardProps) {
  const theme = useTheme();
  const style = theme.palette.accent[tone];

  return (
    <Box
      component={Link}
      to={to}
      sx={{
        flex: { xs: "1 1 auto", md: 1 },
        minWidth: 0,
        background: style.wash,
        border: "1px solid var(--color-border-soft)",
        borderRadius: "22px",
        padding: { xs: "20px", lg: "24px" },
        display: "flex",
        alignItems: "center",
        gap: "14px",
        cursor: "pointer",
        textDecoration: "none",
        transition: "transform .16s, box-shadow .16s",
        "@media (hover: hover) and (pointer: fine)": {
          "&:hover": {
            transform: "translateY(-2px)",
            boxShadow: "var(--shadow-card)",
          },
        },
        "&:focus-visible": {
          outline: "3px solid var(--color-action)",
          outlineOffset: 3,
        },
        "@media (prefers-reduced-motion: reduce)": {
          transition: "none",
          "&:hover": { transform: "none" },
        },
      }}
    >
      <Box
        sx={{
          width: 48,
          height: 48,
          borderRadius: "17px",
          background: style.light,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flex: "none",
        }}
      >
        <PhosphorIcon name={icon} size={26} color={style.main} />
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Box sx={{ fontWeight: 700, fontSize: 16, color: "var(--color-text)" }}>{title}</Box>
        {description ? (
          <Box sx={{ fontWeight: 400, fontSize: 12, lineHeight: 1.7, mt: 0.5, color: "var(--color-text-sub2)" }}>{description}</Box>
        ) : null}
      </Box>
      <PhosphorIcon name="ph-bold ph-arrow-right" size={19} color={style.main} />
    </Box>
  );
}
