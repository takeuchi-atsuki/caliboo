import { afterEach, describe, expect, it, vi } from "vitest";
import { clearWorkspaces, loadWorkspace, saveWorkspace, workspaceKey } from "./workspaceStorage";

describe("課題ワークスペースの一時保存", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("利用者・課題ごとに分離し、ログアウト時は対象データだけ消す", () => {
    expect(saveWorkspace(1, 10, "code a")).toBe(true);
    expect(saveWorkspace(2, 10, "code b")).toBe(true);
    expect(saveWorkspace(1, 11, "code c")).toBe(true);
    sessionStorage.setItem("other", "keep");
    expect(loadWorkspace(1, 10)).toBe("code a");
    expect(loadWorkspace(2, 10)).toBe("code b");
    expect(loadWorkspace(1, 11)).toBe("code c");
    expect(loadWorkspace(1, 12)).toBe("");
    clearWorkspaces();
    expect(loadWorkspace(1, 10)).toBe("");
    expect(loadWorkspace(2, 10)).toBe("");
    expect(sessionStorage.getItem("other")).toBe("keep");
  });

  it("保存領域が利用できない場合も画面が動き、保存失敗を通知する", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw Error("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw Error("blocked"); });
    vi.spyOn(Storage.prototype, "key").mockImplementation(() => { throw Error("blocked"); });
    expect(loadWorkspace(1, 10)).toBe("");
    expect(saveWorkspace(1, 10, "code")).toBe(false);
    expect(() => clearWorkspaces()).not.toThrow();
    expect(workspaceKey(1, 10)).toContain("1.10");
  });
});
