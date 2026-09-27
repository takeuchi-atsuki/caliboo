import { useEffect } from "react";
import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import type { SxProps, Theme } from "@mui/material/styles";

import { PhosphorIcon } from "../icon/PhosphorIcon";

export interface CollapsibleAsideProps {
  children: ReactNode;
  open: boolean;
  onClose: () => void;
  anchor?: "left" | "right";
  width: number;
  title: string;
  sx?: SxProps<Theme>;
}

// Drawerはポータル経由で描画されるため、display:flexの親内に置いても幅を消費しない。
export function CollapsibleAside({ children, open, onClose, anchor = "left", width, title, sx }: CollapsibleAsideProps) {
  const theme = useTheme();
  const isCompact = useMediaQuery(theme.breakpoints.down("md"));

  // コンパクト表示でなくなった際に開閉状態をリセットし、再度狭めた時に意図せず開いた状態にならないようにする。
  useEffect(() => {
    if (!isCompact) onClose();
  }, [isCompact]);

  if (!isCompact) {
    return (
      <Box component="aside" sx={{ width, flex: "none", ...sx }}>
        {children}
      </Box>
    );
  }

  return (
    <Drawer
      anchor={anchor}
      open={open}
      onClose={onClose}
      ModalProps={{ keepMounted: true }}
      slotProps={{ paper: { sx: { maxWidth: "100vw" } } }}
    >
      <Box sx={{ width, maxWidth: "100vw", ...sx }} role="dialog" aria-label={title}>
        <Box sx={{ display: "flex", justifyContent: "flex-end", padding: "8px 8px 0" }}>
          <IconButton onClick={onClose} aria-label="閉じる" size="small">
            <PhosphorIcon name="ph-bold ph-x" size={16} color="var(--color-text)" />
          </IconButton>
        </Box>
        {children}
      </Box>
    </Drawer>
  );
}
