import { describe, it, expect } from "vitest";

import { toneForDeptColor } from "./deptColor";

describe("toneForDeptColor", () => {
  it.each([
    ["#d6ebff", "blue"],
    ["#cdeede", "green"],
    ["#ffd9e6", "pink"],
    ["#e3ddff", "purple"],
    ["#ffe9c7", "orange"],
  ] as const)("既知のhex %s をTone %s に解決する", (hex, tone) => {
    expect(toneForDeptColor(hex)).toBe(tone);
  });

  it("大文字hexも小文字と同じTone扱いになる", () => {
    expect(toneForDeptColor("#D6EBFF")).toBe("blue");
  });

  it("未知のhexはnullを返す", () => {
    expect(toneForDeptColor("#f4f0ec")).toBeNull();
  });
});
