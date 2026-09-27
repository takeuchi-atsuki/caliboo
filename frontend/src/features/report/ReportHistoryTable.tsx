import { useRef } from "react";
import Table from "@mui/material/Table";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableBody from "@mui/material/TableBody";
import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import Box from "@mui/material/Box";

import { MOOD_OPTIONS } from "../../lib/moodOptions";
import type { ReportHistoryItem } from "../../lib/types";

export interface ReportHistoryTableProps {
  items: ReportHistoryItem[];
  onSelect: (item: ReportHistoryItem) => void;
}

const headerCellSx = {
  textAlign: "left" as const,
  fontSize: 11.5,
  color: "var(--color-text-sub)",
  fontWeight: 700,
  paddingBottom: "8px",
  borderBottom: "1.5px solid var(--color-bg)",
  position: "sticky" as const,
  top: 0,
  background: "var(--color-panel)",
  zIndex: 1,
};

// デザインカンプ上の見た目(通常のテキスト)を変えないよう、ブラウザ既定のボタン装飾を打ち消す。フォーカスリングはブラウザ既定のまま残す
const dateButtonSx = {
  background: "none",
  border: 0,
  padding: 0,
  font: "inherit",
  color: "inherit",
  cursor: "pointer",
};

const HISTORY_TABLE_MAX_HEIGHT = 360;

export function ReportHistoryTable({ items, onSelect }: ReportHistoryTableProps) {
  if (items.length === 0) {
    return <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>まだ提出した日報はありません。</Box>;
  }

  return (
    <TableContainer sx={{ maxHeight: HISTORY_TABLE_MAX_HEIGHT, overflowY: "auto" }}>
      <Table sx={{ width: "100%", borderCollapse: "collapse" }}>
        <TableHead>
          <TableRow>
            <TableCell sx={headerCellSx}>日付</TableCell>
            <TableCell sx={headerCellSx}>感じたこと</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item, index) => (
            <ReportHistoryRow key={`${item.date}-${index}`} item={item} onSelect={onSelect} />
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

interface ReportHistoryRowProps {
  item: ReportHistoryItem;
  onSelect: (item: ReportHistoryItem) => void;
}

/**
 * !NOTE: 日付ボタンは自前の`onClick`を持たず、クリック(Enter/Spaceによるclickを含む)を
 *        行の`onClick`へバブリングさせて`onSelect`を1箇所で呼ぶ。
 *        行の`onClick`で日付ボタンへ`focus()`しているのは、日付以外のセルのクリックや、
 *        クリックでボタンにフォーカスしないブラウザ(macOSのSafari/Firefox)でも、
 *        ダイアログを閉じたときのフォーカス復帰先をこの行の日付ボタンにするため。
 */
function ReportHistoryRow({ item, onSelect }: ReportHistoryRowProps) {
  const dateButtonRef = useRef<HTMLButtonElement>(null);

  return (
    <TableRow
      onClick={() => {
        dateButtonRef.current?.focus();
        onSelect(item);
      }}
      sx={{
        cursor: "pointer",
        "&:hover": { background: "var(--color-panel)" },
      }}
    >
      <TableCell sx={{ fontSize: 13, color: "var(--color-text)", padding: "10px 0", borderBottom: "1px solid var(--color-bg)" }}>
        <Box
          component="button"
          type="button"
          ref={dateButtonRef}
          aria-label={`${item.date}の日報を開く`}
          sx={dateButtonSx}
        >
          {item.date}
        </Box>
      </TableCell>
      <TableCell sx={{ padding: "10px 0", borderBottom: "1px solid var(--color-bg)" }}>
        {item.mood.length === 0 ? (
          <Box component="span" sx={{ color: "var(--color-text-sub)" }}>
            —
          </Box>
        ) : (
          <Box sx={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {item.mood.map((mood) => {
              const option = MOOD_OPTIONS.find((o) => o.value === mood);
              if (!option) return null;
              return (
                <Box
                  component="span"
                  key={mood}
                  sx={{
                    background: option.bg,
                    color: option.fg,
                    padding: "4px 12px",
                    borderRadius: "12px",
                    fontWeight: 700,
                    fontSize: 12,
                  }}
                >
                  {option.label}
                </Box>
              );
            })}
          </Box>
        )}
      </TableCell>
    </TableRow>
  );
}
