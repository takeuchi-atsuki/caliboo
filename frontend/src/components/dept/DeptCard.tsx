import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import ListItemButton from "@mui/material/ListItemButton";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

import type { Department } from "../../lib/types";
import { toneForDeptColor } from "../../lib/deptColor";
import { PhosphorIcon } from "../icon/PhosphorIcon";

export interface DeptCardProps {
  dept: Department;
  selected?: boolean;
  onSelect: (id: string) => void;
  layout?: "grid" | "list";
}

export function DeptCard({ dept, selected, onSelect, layout = "grid" }: DeptCardProps) {
  const theme = useTheme();
  const tone = toneForDeptColor(dept.color);
  const background = tone ? theme.palette.accent[tone].light : "var(--color-bg-alt)";

  if (layout === "list") {
    return (
      <ListItemButton
        selected={selected}
        onClick={() => onSelect(dept.id)}
        sx={{
          display: "flex",
          gap: "11px",
          padding: "11px 13px",
          borderRadius: "14px",
          alignItems: "center",
          "&.Mui-selected, &.Mui-selected:hover": { background: "var(--color-green-100)" },
        }}
      >
        <Box
          sx={{
            width: 34,
            height: 34,
            borderRadius: "11px",
            background,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flex: "none",
          }}
        >
          <PhosphorIcon name={dept.icon} size={17} color="var(--color-text)" />
        </Box>
        <Box
          component="span"
          sx={{
            fontWeight: selected ? 700 : 600,
            fontSize: 13.5,
            color: selected ? "var(--color-green-500)" : "var(--color-text-sub2)",
          }}
        >
          {dept.name}
        </Box>
      </ListItemButton>
    );
  }

  return (
    <Card
      sx={{
        background,
        borderRadius: "20px",
        boxShadow: "none",
        transition: "transform .16s, box-shadow .16s",
        "@media (hover: hover) and (pointer: fine)": {
          "&:hover": {
            transform: "translateY(-2px)",
            boxShadow: "var(--shadow-card)",
          },
        },
        "&:focus-within": {
          outline: "3px solid var(--color-action)",
          outlineOffset: 3,
        },
        "@media (prefers-reduced-motion: reduce)": { transition: "none", "&:hover": { transform: "none" } },
      }}
    >
      <CardActionArea onClick={() => onSelect(dept.id)} sx={{ padding: "22px" }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Box
            sx={{
              width: 50,
              height: 50,
              borderRadius: "16px",
              background: "color-mix(in srgb, var(--color-panel) 70%, transparent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <PhosphorIcon name={dept.icon} size={25} color="var(--color-text)" />
          </Box>
          <PhosphorIcon name="ph-bold ph-arrow-right" size={20} color="var(--color-text)" />
        </Box>
        <Box sx={{ fontWeight: 800, fontSize: 19, color: "var(--color-text)", marginTop: "16px" }}>{dept.name}</Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "6px" }}>
          <PhosphorIcon name="ph-fill ph-books" size={14} color="var(--color-text)" />
          <Box component="span" sx={{ fontWeight: 600, fontSize: 12, color: "var(--color-text)" }}>
            ナレッジ {dept.knowledgeCount}件
          </Box>
        </Box>
      </CardActionArea>
    </Card>
  );
}
