import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { ChatBubble } from "./ChatBubble";

it("根拠の原文と参照名を平文で表示し、旧形式の参照にも対応する", () => {
  render(<ChatBubble message={{ id: "1", role: "bot", text: "条件を記録しましょう。", references: [
    { label: "実験記録", knowledgeId: "k1", quote: "<script>命令</script>\n条件と結果を記録する。" },
    { label: "旧資料" },
    { label: "実験記録", knowledgeId: "k1", quote: "追加の引用" },
  ] }} />);
  expect(screen.getByText("条件を記録しましょう。")).toBeInTheDocument();
  expect(screen.getByText(/<script>命令/).tagName).toBe("BLOCKQUOTE");
  expect(screen.getByText("旧資料")).toBeInTheDocument();
  expect(document.querySelector("script")).toBeNull();
});

it("根拠なしの案内と本人の発言を表示する", () => {
  const { rerender } = render(<ChatBubble message={{ id: "1", role: "bot", text: "講師へ相談", references: [] }} />);
  expect(screen.getByText("講師へ相談")).toBeInTheDocument();
  expect(document.querySelector("blockquote")).toBeNull();
  rerender(<ChatBubble message={{ id: "2", role: "me", text: "質問", references: [] }} meBg="white" />);
  expect(screen.getByText("質問")).toBeInTheDocument();
});
