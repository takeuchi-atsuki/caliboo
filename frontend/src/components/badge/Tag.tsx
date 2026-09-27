import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

import type { Tone } from "../../lib/types";

export interface TagProps {
  label: string;
  tone?: Tone;
}

export function Tag({ label, tone = "green" }: TagProps) {
  const theme = useTheme();
  const style = theme.palette.accent[tone];

  return (
    <Box
      component="span"
      sx={{
        display: "inline-flex",
        padding: "7px 13px",
        borderRadius: "20px",
        fontWeight: 700,
        fontSize: 12.5,
        background: style.wash,
        color: style.main,
      }}
    >
      {label}
    </Box>
  );
}
