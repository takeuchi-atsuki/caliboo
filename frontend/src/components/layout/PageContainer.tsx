import type { ReactNode } from "react";
import Box from "@mui/material/Box";

import { TopNav } from "./TopNav";

export function PageContainer({ children }: { children: ReactNode }) {
  return (
    <Box sx={{ minHeight: "100dvh", background: "var(--color-bg)", display: "flex", flexDirection: "column", pb: { xs: "calc(80px + env(safe-area-inset-bottom, 0px))", sm: 0 } }}>
      <a className="skip-link" href="#app-content">本文へ移動</a>
      <TopNav />
      <Box id="app-content" tabIndex={-1} sx={{ flex: 1, display: "flex", flexDirection: "column", width: "100%", maxWidth: 1440, mx: "auto", minWidth: 0, outline: "none" }}>{children}</Box>
    </Box>
  );
}
