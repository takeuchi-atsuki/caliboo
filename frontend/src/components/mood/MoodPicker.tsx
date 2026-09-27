import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import ToggleButton from "@mui/material/ToggleButton";

import type { Mood } from "../../lib/types";
import { MOOD_OPTIONS } from "../../lib/moodOptions";

export interface MoodPickerProps {
  value: Mood[];
  onChange: (moods: Mood[]) => void;
}

/**
 * !NOTE: `ToggleButtonGroup`は`exclusive`未指定時は複数選択可能で、
 *        `onChange`が選択中の値の配列をそのまま返すため、自前のtoggleロジックは不要。
 */
export function MoodPicker({ value, onChange }: MoodPickerProps) {
  return (
    <ToggleButtonGroup
      value={value}
      onChange={(_event, newValue: Mood[]) => onChange(newValue)}
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: "8px",
        margin: "12px 0",
        "& .MuiToggleButtonGroup-grouped": {
          margin: 0,
          border: "none",
          borderRadius: "20px !important",
        },
      }}
    >
      {MOOD_OPTIONS.map((option) => (
        <ToggleButton
          key={option.value}
          value={option.value}
          disableRipple
          sx={{
            padding: "8px 15px",
            minHeight: 44,
            fontWeight: 700,
            fontSize: 12.5,
            textTransform: "none",
            background: "var(--color-bg)",
            color: "var(--color-text-sub2)",
            "&.Mui-selected, &.Mui-selected:hover": {
              background: option.bg,
              color: option.fg,
            },
          }}
        >
          {option.label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}
