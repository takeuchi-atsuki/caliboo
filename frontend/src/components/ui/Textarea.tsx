import type { TextareaHTMLAttributes } from "react";
import InputBase from "@mui/material/InputBase";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  borderColor?: string;
  bgColor?: string;
}

/**
 * !NOTE: `TextField`は未使用のラベル領域を持つため、装飾のないMUI `InputBase`を
 *        multiline指定で使い、見た目(枠線・背景・角丸・高さ)をsxで指定している。
 */
export function Textarea({
  borderColor = "var(--color-green-100)",
  bgColor = "var(--color-bg)",
  style,
  ...rest
}: TextareaProps) {
  return (
    <InputBase
      multiline
      fullWidth
      style={style}
      sx={{
        border: `1.5px solid ${borderColor}`,
        background: bgColor,
        borderRadius: "13px",
        padding: "13px",
        "& .MuiInputBase-input": {
          height: "119px !important",
          font: "400 16px/1.8 var(--font-body)",
          color: "var(--color-text)",
          resize: "none",
          overflow: "auto",
          padding: 0,
        },
      }}
      {...(rest as Record<string, unknown>)}
    />
  );
}
