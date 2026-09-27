import type { ButtonHTMLAttributes } from "react";
import MuiButton from "@mui/material/Button";

import { PhosphorIcon } from "../icon/PhosphorIcon";

export type ButtonVariant = "primary" | "secondary";

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "color"> {
  variant?: ButtonVariant;
  accentColor?: string;
  icon?: string;
}

export function Button({
  variant = "primary",
  accentColor = "var(--color-green-400)",
  icon,
  children,
  style,
  ...rest
}: ButtonProps) {
  const variantSx =
    variant === "primary"
      ? {
          background: accentColor,
          color: "var(--color-on-pastel)",
          boxShadow: "none",
          border: "none",
        }
      : {
          background: "var(--color-panel)",
          color: "var(--color-text)",
          border: "1px solid var(--color-border)",
        };

  return (
    // disableRipple/textTransform: "none"はデザインカンプの見た目(ripple・大文字化なし)を保つため
    <MuiButton
      disableRipple
      disableElevation
      style={style}
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: "7px",
        minHeight: 44,
        padding: "11px 20px",
        borderRadius: "14px",
        fontWeight: 700,
        fontSize: 14,
        textTransform: "none",
        cursor: "pointer",
        ...variantSx,
        "&:hover": { ...variantSx, filter: "brightness(.97)" },
        "&:active": { filter: "brightness(.93)" },
        "&.Mui-disabled": { background: "var(--color-bg-alt)", color: "var(--color-text-sub)", border: "1px solid var(--color-border-soft)", boxShadow: "none" },
      }}
      {...rest}
    >
      {icon ? <PhosphorIcon name={icon} /> : null}
      {children}
    </MuiButton>
  );
}
