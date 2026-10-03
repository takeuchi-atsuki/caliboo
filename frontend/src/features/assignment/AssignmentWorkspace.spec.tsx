import { afterEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { AssignmentWorkspace } from "./AssignmentWorkspace";
import { runJavaScript } from "./sandboxRunner";

vi.mock("./sandboxRunner", () => ({ runJavaScript: vi.fn() }));
const mockedRun = vi.mocked(runJavaScript);

afterEach(() => {
  sessionStorage.clear();
  vi.clearAllMocks();
});

it("コードを実行して出力を表示し、回答欄へ反映できる", async () => {
  mockedRun.mockResolvedValue({ output: ["hello"], timedOut: false });
  const onUseCode = vi.fn();
  render(<AssignmentWorkspace assignmentId={10} userId={1} canUseCode onUseCode={onUseCode} />);
  fireEvent.change(screen.getByRole("textbox", { name: "main.js のコード" }), {
    target: { value: "console.log('hello')" },
  });
  fireEvent.click(screen.getByRole("button", { name: "実行" }));
  await waitFor(() => expect(screen.getByRole("log")).toHaveTextContent("hello"));
  expect(mockedRun).toHaveBeenCalledWith("console.log('hello')");
  fireEvent.click(screen.getByRole("button", { name: "コードを回答欄へ反映" }));
  expect(onUseCode).toHaveBeenCalledWith("console.log('hello')");
  expect(sessionStorage.getItem("caliboo.assignment-workspace.1.10")).toBe("console.log('hello')");
});

it("コマンドで内容を確認・消去でき、レビュー済み課題では回答欄へ反映できない", () => {
  sessionStorage.setItem("caliboo.assignment-workspace.1.10", "print('saved')");
  render(<AssignmentWorkspace assignmentId={10} userId={1} canUseCode={false} onUseCode={vi.fn()} />);
  expect(screen.getByRole("textbox", { name: "main.js のコード" })).toHaveValue("print('saved')");
  expect(screen.getByRole("button", { name: "コードを回答欄へ反映" })).toBeDisabled();
  const command = screen.getByRole("textbox", { name: "コマンド" });
  const form = command.closest("form")!;
  fireEvent.change(command, { target: { value: "cat main.js" } });
  fireEvent.submit(form);
  expect(screen.getByRole("log")).toHaveTextContent("print('saved')");
  fireEvent.change(command, { target: { value: "clear" } });
  fireEvent.submit(form);
  expect(screen.getByRole("log")).toBeEmptyDOMElement();
});

it("空のコードと実行エラーを説明する", async () => {
  mockedRun.mockRejectedValueOnce(Error("worker failed"));
  render(<AssignmentWorkspace assignmentId={10} userId={1} canUseCode onUseCode={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "実行" }));
  expect(screen.getByRole("log")).toHaveTextContent("main.js にコードを入力");
  fireEvent.change(screen.getByRole("textbox", { name: "main.js のコード" }), { target: { value: "bad()" } });
  fireEvent.click(screen.getByRole("button", { name: "実行" }));
  await waitFor(() => expect(screen.getByRole("log")).toHaveTextContent("実行環境でエラー"));
});
