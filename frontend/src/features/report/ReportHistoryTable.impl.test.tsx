import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { ReportHistoryTable } from "./ReportHistoryTable";
import type { ReportHistoryItem } from "../../lib/types";

describe("ReportHistoryTable", () => {
  it("MOOD_OPTIONSに無いきもちの値は読み飛ばし、既知の値だけをラベルで表示する", () => {
    // APIが型の範囲外の値を返した場合の防御分岐を検証するため、型を外して渡す
    const item = {
      date: "2026-09-25",
      keep: "",
      problem: "",
      try: "",
      mood: ["happy", "unknown"],
      moodComment: "",
    } as unknown as ReportHistoryItem;
    render(<ReportHistoryTable items={[item]} onSelect={() => {}} />);
    const cells = within(screen.getAllByRole("row")[1]).getAllByRole("cell");
    expect(cells[1]).toHaveTextContent(/^うれしい$/);
  });
});
