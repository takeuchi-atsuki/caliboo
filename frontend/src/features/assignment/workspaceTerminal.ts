export type TerminalCommand =
  | { kind: "help" | "list" | "run" | "clear" }
  | { kind: "show" }
  | { kind: "error"; message: string };

export function parseTerminalCommand(input: string): TerminalCommand {
  const parts = input.trim().split(/\s+/);
  const command = parts[0]?.toLowerCase();
  if (command === "help" && parts.length === 1) return { kind: "help" };
  if (command === "ls" && parts.length === 1) return { kind: "list" };
  if (command === "run" && parts.length === 1) return { kind: "run" };
  if (command === "clear" && parts.length === 1) return { kind: "clear" };
  if (command === "cat" && parts.length === 2 && parts[1] === "main.js") return { kind: "show" };
  return { kind: "error", message: "不明なコマンドです。help で使用できるコマンドを確認してください。" };
}
