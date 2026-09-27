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
          color: "var(--color-panel)",
          boxShadow: `0 8px 18px color-mix(in srgb, ${accentColor} 40%, transparent)`,
          border: "none",
        }
      : {
          background: "var(--color-panel)",
          color: "var(--color-text-sub2)",
          border: "1px solid var(--color-border)",
        };

  return (
    // disableRipple/textTransform: "none"はデザインカンプの見た目(ripple・大文字化なし)を保つため
    <MuiButton
      disableRipple
      disableElevation
      style={style}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: "7px",
        padding: "11px 24px",
        borderRadius: "14px",
        fontWeight: 800,
        fontSize: 13.5,
        textTransform: "none",
        cursor: "pointer",
        ...variantSx,
        "&:hover": variantSx,
      }}
      {...rest}
    >
      {icon ? <PhosphorIcon name={icon} /> : null}
      {children}
    </MuiButton>
  );
}
