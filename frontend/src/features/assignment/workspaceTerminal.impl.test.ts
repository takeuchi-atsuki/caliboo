import { describe, expect, it } from "vitest";
import { parseTerminalCommand } from "./workspaceTerminal";

describe("課題ターミナルのコマンド", () => {
  it("許可したコマンドを解釈する", () => {
    expect(parseTerminalCommand(" help ")).toEqual({ kind: "help" });
    expect(parseTerminalCommand("LS")).toEqual({ kind: "list" });
    expect(parseTerminalCommand("cat main.js")).toEqual({ kind: "show" });
    expect(parseTerminalCommand("run")).toEqual({ kind: "run" });
    expect(parseTerminalCommand("clear")).toEqual({ kind: "clear" });
  });

  it("任意のシェルコマンドと引数を拒否する", () => {
    expect(parseTerminalCommand("cat other.js").kind).toBe("error");
    expect(parseTerminalCommand("run extra").kind).toBe("error");
    expect(parseTerminalCommand("curl example.com").kind).toBe("error");
    expect(parseTerminalCommand("").kind).toBe("error");
  });
});
