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
  const shadow = `color-mix(in srgb, ${style.main} 20%, transparent)`;

  return (
    <Box
      component={Link}
      to={to}
      sx={{
        flex: { xs: "1 1 auto", md: 1 },
        background: style.light,
        borderRadius: "22px",
        padding: "24px",
        display: "flex",
        alignItems: "center",
        gap: "16px",
        cursor: "pointer",
        textDecoration: "none",
        transition: "transform .16s, box-shadow .16s",
        "@media (prefers-reduced-motion: reduce)": {
          transition: "none",
        },
        "@media (hover: hover) and (pointer: fine)": {
          "&:hover": {
            transform: "translateY(-5px)",
            boxShadow: `0 18px 32px ${shadow}`,
          },
        },
        "&:focus-visible": {
          transform: "translateY(-5px)",
          boxShadow: `0 18px 32px ${shadow}`,
        },
      }}
    >
      <Box
        sx={{
          width: 54,
          height: 54,
          borderRadius: "17px",
          background: "color-mix(in srgb, var(--color-panel) 65%, transparent)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flex: "none",
        }}
      >
        <PhosphorIcon name={icon} size={26} color={style.main} />
      </Box>
      <Box sx={{ flex: 1 }}>
        <Box sx={{ fontWeight: 800, fontSize: 18, color: "var(--color-text)" }}>{title}</Box>
        {description ? (
          <Box sx={{ fontWeight: 500, fontSize: 12, color: style.main }}>{description}</Box>
        ) : null}
      </Box>
      <PhosphorIcon name="ph-bold ph-arrow-right" size={19} color={style.main} />
    </Box>
  );
}
