import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";

export interface QuickQuestionChipsProps {
  questions: string[];
  onSelect: (question: string) => void;
  hoverColor?: string;
}

export function QuickQuestionChips({ questions, onSelect, hoverColor = "var(--color-blue-500)" }: QuickQuestionChipsProps) {
  return (
    <Box sx={{ display: "flex", gap: "8px", marginBottom: "11px", flexWrap: "wrap" }}>
      {questions.map((question) => (
        <Chip
          key={question}
          label={question}
          onClick={() => onSelect(question)}
          sx={{
            height: "auto",
            minHeight: 44,
            maxWidth: "100%",
            background: "var(--color-bg-alt)",
            borderRadius: "14px",
            fontWeight: 600,
            fontSize: 12,
            color: "var(--color-text-sub2)",
            "& .MuiChip-label": { padding: "8px 14px", whiteSpace: "normal" },
            "@media (hover: hover) and (pointer: fine)": {
              "&:hover": { background: "var(--color-bg-alt)", color: hoverColor },
            },
            "&:focus-visible": { color: hoverColor },
          }}
        />
      ))}
    </Box>
  );
}
