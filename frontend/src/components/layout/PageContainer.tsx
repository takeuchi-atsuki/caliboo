import type { ReactNode } from "react";
import Box from "@mui/material/Box";

import { TopNav } from "./TopNav";

export function PageContainer({ children }: { children: ReactNode }) {
  return (
    <Box sx={{ minHeight: "100vh", background: "var(--color-bg)", display: "flex", flexDirection: "column" }}>
      <TopNav />
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column" }}>{children}</Box>
    </Box>
  );
}
