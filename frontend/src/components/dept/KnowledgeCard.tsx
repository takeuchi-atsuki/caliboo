import Box from "@mui/material/Box";

import type { KnowledgeItem } from "../../lib/types";

export function KnowledgeCard({ item }: { item: KnowledgeItem }) {
  return (
    <Box
      sx={{
        border: "1px solid var(--color-border-soft)",
        borderRadius: "14px",
        padding: "13px",
        overflowWrap: "anywhere",
        cursor: "pointer",
        "@media (hover: hover) and (pointer: fine)": {
          "&:hover": {
            background: "var(--color-blue-100)",
            borderColor: "var(--color-blue-200)",
          },
        },
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <i className="ph ph-file-text" style={{ color: "var(--color-blue-500)", fontSize: 15 }} />
        <Box component="span" sx={{ minWidth: 0, fontWeight: 700, fontSize: 13, color: "var(--color-text)" }}>
          {item.title}
        </Box>
      </Box>
      <Box sx={{ fontWeight: 500, fontSize: 11, color: "var(--color-text-sub)", paddingLeft: "24px", marginTop: "4px" }}>
        {item.description}
      </Box>
    </Box>
  );
}
