const PREFIX = "caliboo.assignment-workspace.";

export function workspaceKey(userId: number, assignmentId: number): string {
  return `${PREFIX}${userId}.${assignmentId}`;
}

export function loadWorkspace(userId: number, assignmentId: number): string {
  try {
    return sessionStorage.getItem(workspaceKey(userId, assignmentId)) ?? "";
  } catch {
    return "";
  }
}

export function saveWorkspace(userId: number, assignmentId: number, code: string): boolean {
  try {
    sessionStorage.setItem(workspaceKey(userId, assignmentId), code);
    return true;
  } catch {
    return false;
  }
}

export function clearWorkspaces(): void {
  try {
    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = sessionStorage.key(index);
      if (key?.startsWith(PREFIX)) sessionStorage.removeItem(key);
    }
  } catch {
    // 保存領域が使えない環境では、保持できる下書きもない。
  }
}
