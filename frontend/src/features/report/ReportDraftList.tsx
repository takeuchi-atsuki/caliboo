import { useState } from "react";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import IconButton from "@mui/material/IconButton";
import Box from "@mui/material/Box";

import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { PhosphorIcon } from "../../components/icon/PhosphorIcon";
import type { ReportDraftItem } from "../../lib/types";

export interface ReportDraftListProps {
  items: ReportDraftItem[];
  onSelect: (item: ReportDraftItem) => void;
  onDelete: (id: number) => void;
}

function previewText(item: ReportDraftItem): string {
  const text = item.keep || item.problem || item.try;
  if (!text) return "（本文未入力）";
  return text.length > 28 ? `${text.slice(0, 28)}…` : text;
}

export function ReportDraftList({ items, onSelect, onDelete }: ReportDraftListProps) {
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

  if (items.length === 0) {
    return (
      <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>保存された下書きはありません。</Box>
    );
  }

  return (
    <>
      <List sx={{ display: "flex", flexDirection: "column", gap: "8px", padding: 0 }}>
        {items.map((item) => (
          <ListItem
            key={item.id}
            disablePadding
            sx={{ border: "1px solid var(--color-bg)", borderRadius: "13px", overflow: "hidden" }}
            secondaryAction={
              <IconButton
                onClick={() => setPendingDeleteId(item.id)}
                aria-label="下書きを削除"
                size="small"
                sx={{ color: "var(--color-text-sub)", fontSize: 16 }}
              >
                <PhosphorIcon name="ph-bold ph-trash" size={16} />
              </IconButton>
            }
          >
            <ListItemButton
              onClick={() => onSelect(item)}
              sx={{
                padding: "10px 12px",
                "@media (hover: hover) and (pointer: fine)": {
                  "&:hover": { background: "var(--color-panel)" },
                },
              }}
            >
              <Box>
                <Box sx={{ fontWeight: 800, fontSize: 13.5, color: "var(--color-text)" }}>{item.date}</Box>
                <Box sx={{ fontWeight: 500, fontSize: 12, color: "var(--color-text-sub)" }}>{previewText(item)}</Box>
              </Box>
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="下書きの削除"
        message="この下書きを削除しますか？元に戻せません。"
        onCancel={() => setPendingDeleteId(null)}
        onConfirm={() => {
          if (pendingDeleteId !== null) {
            onDelete(pendingDeleteId);
          }
          setPendingDeleteId(null);
        }}
      />
    </>
  );
}
