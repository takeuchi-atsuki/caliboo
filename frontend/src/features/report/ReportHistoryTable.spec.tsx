import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ReportHistoryTable } from "./ReportHistoryTable";
import type { ReportHistoryItem } from "../../lib/types";

const ITEMS: ReportHistoryItem[] = [
  { date: "2026-09-25", keep: "K1", problem: "P1", try: "T1", mood: ["happy"], moodComment: "" },
  { date: "2026-09-24", keep: "K2", problem: "P2", try: "T2", mood: [], moodComment: "" },
];

function renderTable(items: ReportHistoryItem[] = ITEMS) {
  const onSelect = vi.fn();
  render(<ReportHistoryTable items={items} onSelect={onSelect} />);
  return { onSelect };
}

describe("ReportHistoryTable", () => {
  it("行のARIAロールをbuttonで上書きせず、テーブルの行/セル構造を保つ", () => {
    renderTable();
    expect(screen.getAllByRole("columnheader").map((header) => header.textContent)).toEqual(["日付", "感じたこと"]);
    // ヘッダー行 + データ行2件
    const rows = screen.getAllByRole("row");
    expect(rows).toHaveLength(3);
    for (const row of rows) {
      expect(row).not.toHaveAttribute("role", "button");
      expect(row).not.toHaveAttribute("tabindex");
    }
    for (const row of rows.slice(1)) {
      expect(within(row).getAllByRole("cell")).toHaveLength(2);
    }
  });

  it("感じたこと未選択の行は「—」を表示する", () => {
    renderTable();
    const cells = within(screen.getAllByRole("row")[2]).getAllByRole("cell");
    expect(cells[1]).toHaveTextContent("—");
  });

  it("日付セル内のボタンをクリックすると、その行の日報でonSelectを1回だけ呼ぶ", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderTable();
    await user.click(screen.getByRole("button", { name: "2026-09-24の日報を開く" }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(ITEMS[1]);
  });

  it("Tabキーで日付ボタンにフォーカスし、Enterキーでその行の日報を1回だけ開ける", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderTable();
    await user.tab();
    expect(screen.getByRole("button", { name: "2026-09-25の日報を開く" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(ITEMS[0]);
  });

  it("Spaceキーでも日付ボタンからその行の日報を1回だけ開ける", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderTable();
    await user.tab();
    await user.tab();
    expect(screen.getByRole("button", { name: "2026-09-24の日報を開く" })).toHaveFocus();
    await user.keyboard(" ");
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(ITEMS[1]);
  });

  it("日付以外のセル(感じたこと)をクリックしても、その行の日報でonSelectを呼ぶ", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderTable();
    await user.click(screen.getByText("—"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(ITEMS[1]);
  });

  it("日付以外のセルをクリックすると、その行の日付ボタンにフォーカスが移る(ダイアログを閉じたときの復帰先にするため)", async () => {
    const user = userEvent.setup();
    renderTable();
    await user.click(screen.getByText("—"));
    expect(screen.getByRole("button", { name: "2026-09-24の日報を開く" })).toHaveFocus();
  });

  it("同じ日付の履歴が複数ある場合、同名のボタンが並び、クリックした行の日報でonSelectを呼ぶ", async () => {
    const user = userEvent.setup();
    const sameDateItems: ReportHistoryItem[] = [
      { ...ITEMS[0], keep: "後に提出" },
      { ...ITEMS[0], keep: "先に提出" },
    ];
    const { onSelect } = renderTable(sameDateItems);
    const buttons = screen.getAllByRole("button", { name: "2026-09-25の日報を開く" });
    expect(buttons).toHaveLength(2);
    await user.click(buttons[1]);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(sameDateItems[1]);
  });

  it("履歴が0件のときは表の代わりに案内文を表示する", () => {
    renderTable([]);
    expect(screen.getByText("まだ提出した日報はありません。")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
