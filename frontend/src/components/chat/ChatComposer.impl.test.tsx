import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ChatComposer } from "./ChatComposer";

function renderComposer(value: string) {
  const onSend = vi.fn();
  render(<ChatComposer value={value} onChange={() => {}} onSend={onSend} />);
  return { onSend, input: screen.getByPlaceholderText("メッセージを入力…") };
}

describe("ChatComposer", () => {
  it("入力がある状態でEnterを押すとonSendを呼ぶ", () => {
    const { onSend, input } = renderComposer("こんにちは");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSend).toHaveBeenCalledTimes(1);
  });

  it("IME変換中(isComposing)のEnterではonSendを呼ばない", () => {
    const { onSend, input } = renderComposer("こんにちは");
    fireEvent.keyDown(input, { key: "Enter", isComposing: true });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("keyCode 229(Safariの変換確定)のEnterではonSendを呼ばない", () => {
    const { onSend, input } = renderComposer("こんにちは");
    fireEvent.keyDown(input, { key: "Enter", keyCode: 229 });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("入力が空白のみの場合はEnterでもonSendを呼ばない", () => {
    const { onSend, input } = renderComposer("   ");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("Enter以外のキーではonSendを呼ばない", () => {
    const { onSend, input } = renderComposer("こんにちは");
    fireEvent.keyDown(input, { key: "a" });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("入力がある状態で送信ボタンをクリックするとonSendを呼ぶ", async () => {
    const user = userEvent.setup();
    const { onSend } = renderComposer("こんにちは");
    await user.click(screen.getByRole("button", { name: "送信" }));
    expect(onSend).toHaveBeenCalledTimes(1);
  });

  it("入力が空白のみの場合は送信ボタンのクリックでもonSendを呼ばない", async () => {
    const user = userEvent.setup();
    const { onSend } = renderComposer("   ");
    await user.click(screen.getByRole("button", { name: "送信" }));
    expect(onSend).not.toHaveBeenCalled();
  });

  it("入力内容の変更をonChangeへ渡す", () => {
    const onChange = vi.fn();
    render(<ChatComposer value="" onChange={onChange} onSend={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText("メッセージを入力…"), { target: { value: "質問" } });
    expect(onChange).toHaveBeenCalledWith("質問");
  });
});
