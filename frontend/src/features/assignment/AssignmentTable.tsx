import { Link as RouterLink } from "react-router-dom";
import Table from "@mui/material/Table";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableBody from "@mui/material/TableBody";
import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import Box from "@mui/material/Box";

import { Tag } from "../../components/badge/Tag";
import { assignmentStatusLabel, assignmentStatusTone } from "../../lib/assignmentStatus";
import type { AssignmentListItem } from "../../lib/types";

export interface AssignmentTableProps {
  items: AssignmentListItem[];
  // !NOTE: 講師(admin)の`status`は常に「本人(=講師)の提出状態」であり意味を持たないため、
  //        講師表示のときは列自体を出さない(docs/screens/assignment.md参照)。
  showStatusColumn?: boolean;
  // 講師表示のときは状態列の代わりに配信先(全員/対象者名)列を出す。
  showTargetColumn?: boolean;
  // 新入社員表示のときに、自分宛ての課題へ「あなた向け」タグを付けるための本人ID。
  currentUserId?: number;
}

const headerCellSx = {
  textAlign: "left" as const,
  fontSize: 11.5,
  color: "var(--color-text-sub)",
  fontWeight: 700,
  paddingBottom: "8px",
  borderBottom: "1.5px solid var(--color-bg)",
};

const bodyCellSx = {
  fontSize: 13,
  color: "var(--color-text)",
  padding: "10px 0",
  borderBottom: "1px solid var(--color-bg)",
};

/**
 * !NOTE: 行クリックは`TableRow`に`role="button"`を付与せず、タイトルセル内の
 *        `Link`を操作要素にしている。行の暗黙的なARIAロール(row)を上書きしないため。
 */
export function AssignmentTable({
  items,
  showStatusColumn = true,
  showTargetColumn = false,
  currentUserId,
}: AssignmentTableProps) {
  if (items.length === 0) {
    return (
      <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>
        課題がまだありません。
      </Box>
    );
  }

  return (
    <TableContainer>
      <Table sx={{ width: "100%", borderCollapse: "collapse" }}>
        <TableHead>
          <TableRow>
            <TableCell sx={headerCellSx}>タイトル</TableCell>
            {showStatusColumn ? <TableCell sx={headerCellSx}>状態</TableCell> : null}
            {showTargetColumn ? <TableCell sx={headerCellSx}>配信先</TableCell> : null}
            <TableCell sx={headerCellSx}>作成日</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id}>
              <TableCell sx={bodyCellSx}>
                <Box sx={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <Box
                    component={RouterLink}
                    to={`/assignments/${item.id}`}
                    sx={{
                      color: "var(--color-green-500)",
                      fontWeight: 700,
                      textDecoration: "none",
                      "&:hover": { textDecoration: "underline" },
                    }}
                  >
                    {item.title}
                  </Box>
                  {!showTargetColumn && item.target && item.target.id === currentUserId ? (
                    <Tag label="あなた向け" tone="purple" />
                  ) : null}
                </Box>
              </TableCell>
              {showStatusColumn ? (
                <TableCell sx={bodyCellSx}>
                  <Tag label={assignmentStatusLabel(item.status)} tone={assignmentStatusTone(item.status)} />
                </TableCell>
              ) : null}
              {showTargetColumn ? (
                <TableCell sx={bodyCellSx}>{item.target ? item.target.displayName : "全員"}</TableCell>
              ) : null}
              <TableCell sx={bodyCellSx}>{item.createdAt.slice(0, 10)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
