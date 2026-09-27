import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { ConfirmDialog } from "./ConfirmDialog";

describe("ConfirmDialog", () => {
  it("confirmColorを指定しない場合、確認ボタンの色は既定(破壊的操作向けのerror)になる", () => {
    render(
      <ConfirmDialog
        open
        title="削除の確認"
        message="削除しますか？"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );

    const button = screen.getByRole("button", { name: "削除する" });
    expect(button.className).toContain("MuiButton-colorError");
  });

  it("confirmColorを指定すると、確認ボタンの色がそれに従う", () => {
    render(
      <ConfirmDialog
        open
        title="配信の確認"
        message="配信しますか？"
        confirmLabel="配信する"
        confirmColor="success"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );

    const button = screen.getByRole("button", { name: "配信する" });
    expect(button.className).toContain("MuiButton-colorSuccess");
  });

  it("confirmDisabledを指定しない場合、確認ボタンは無効化されない", () => {
    render(
      <ConfirmDialog open title="確認" message="実行しますか？" onConfirm={() => {}} onCancel={() => {}} />,
    );

    expect(screen.getByRole("button", { name: "削除する" })).not.toBeDisabled();
  });

  it("confirmDisabledがtrueのとき、確認ボタンが無効化される(送信中の二重実行を防ぐ)", () => {
    render(
      <ConfirmDialog
        open
        title="確認"
        message="実行しますか？"
        confirmDisabled
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );

    expect(screen.getByRole("button", { name: "削除する" })).toBeDisabled();
  });
});
