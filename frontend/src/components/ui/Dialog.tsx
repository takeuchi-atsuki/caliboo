import { useId } from "react";
import type { ReactNode } from "react";
import MuiDialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Box from "@mui/material/Box";

import { PhosphorIcon } from "../icon/PhosphorIcon";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
}

export function Dialog({ open, onClose, title, children }: DialogProps) {
  const titleId = useId();

  return (
    <MuiDialog
      open={open}
      onClose={onClose}
      aria-labelledby={titleId}
      slotProps={{
        backdrop: {
          sx: { backgroundColor: "color-mix(in srgb, var(--color-text) 35%, transparent)" },
        },
        paper: {
          sx: {
            borderRadius: "24px",
            width: 520,
            maxWidth: "calc(100vw - 32px)",
            maxHeight: "calc(100dvh - 48px)",
            margin: "16px",
            boxShadow: "var(--shadow-float)",
          },
        },
      }}
    >
      <DialogTitle
        id={titleId}
        sx={{ display: "flex", justifyContent: "space-between", gap: 1, alignItems: "center", padding: "16px 20px 0" }}
      >
        <Box component="span" sx={{ fontWeight: 800, fontSize: 17, color: "var(--color-text)" }}>
          {title}
        </Box>
        <IconButton onClick={onClose} aria-label="閉じる" size="small" sx={{ color: "var(--color-text-sub)" }}>
          <PhosphorIcon name="ph-bold ph-x" size={18} />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ padding: "16px 20px 24px" }}>{children}</DialogContent>
    </MuiDialog>
  );
}
