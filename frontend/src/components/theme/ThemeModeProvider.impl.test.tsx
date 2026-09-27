import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ThemeModeProvider, useThemeMode } from "./ThemeModeProvider";

const STORAGE_KEY = "caliboo:theme-mode";

function createMatchMediaMock(matches: boolean) {
  const listeners = new Set<(e: MediaQueryListEvent) => void>();
  const mql = {
    matches,
    media: "(prefers-color-scheme: dark)",
    addEventListener: (_: string, listener: (e: MediaQueryListEvent) => void) => {
      listeners.add(listener);
    },
    removeEventListener: (_: string, listener: (e: MediaQueryListEvent) => void) => {
      listeners.delete(listener);
    },
  } as unknown as MediaQueryList;

  return {
    mql,
    emitChange: (nextMatches: boolean) => {
      listeners.forEach((listener) => listener({ matches: nextMatches } as MediaQueryListEvent));
    },
  };
}

function Probe() {
  const { mode, toggleMode } = useThemeMode();
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <button onClick={toggleMode}>toggle</button>
    </div>
  );
}

describe("ThemeModeProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("localStorageに保存値が無い場合、OS設定(prefers-color-scheme)がdarkならdarkで初期化する", () => {
    const { mql } = createMatchMediaMock(true);
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue(mql));

    render(
      <ThemeModeProvider>
        <Probe />
      </ThemeModeProvider>,
    );

    expect(screen.getByTestId("mode").textContent).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("localStorageに保存値が無い場合、OS設定がlightならlightで初期化する", () => {
    const { mql } = createMatchMediaMock(false);
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue(mql));

    render(
      <ThemeModeProvider>
        <Probe />
      </ThemeModeProvider>,
    );

    expect(screen.getByTestId("mode").textContent).toBe("light");
  });

  it("localStorageに保存済みの値がOS設定より優先される", () => {
    window.localStorage.setItem(STORAGE_KEY, "dark");
    const { mql } = createMatchMediaMock(false);
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue(mql));

    render(
      <ThemeModeProvider>
        <Probe />
      </ThemeModeProvider>,
    );

    expect(screen.getByTestId("mode").textContent).toBe("dark");
  });

  it("toggleMode()でmodeが反転し、localStorageに保存され、data-theme属性が追従する", async () => {
    const user = userEvent.setup();
    const { mql } = createMatchMediaMock(false);
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue(mql));

    render(
      <ThemeModeProvider>
        <Probe />
      </ThemeModeProvider>,
    );

    expect(screen.getByTestId("mode").textContent).toBe("light");

    await user.click(screen.getByText("toggle"));

    expect(screen.getByTestId("mode").textContent).toBe("dark");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");

    await user.click(screen.getByText("toggle"));

    expect(screen.getByTestId("mode").textContent).toBe("light");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("明示選択が無い間はOS設定のchangeイベントに追従する", () => {
    const { mql, emitChange } = createMatchMediaMock(false);
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue(mql));

    render(
      <ThemeModeProvider>
        <Probe />
      </ThemeModeProvider>,
    );

    expect(screen.getByTestId("mode").textContent).toBe("light");

    act(() => {
      emitChange(true);
    });

    expect(screen.getByTestId("mode").textContent).toBe("dark");

    act(() => {
      emitChange(false);
    });

    expect(screen.getByTestId("mode").textContent).toBe("light");
  });

  it("明示選択済みの場合はOS設定のchangeイベントに追従しない", async () => {
    const user = userEvent.setup();
    const { mql, emitChange } = createMatchMediaMock(false);
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue(mql));

    render(
      <ThemeModeProvider>
        <Probe />
      </ThemeModeProvider>,
    );

    await user.click(screen.getByText("toggle"));
    expect(screen.getByTestId("mode").textContent).toBe("dark");

    act(() => {
      emitChange(false);
    });

    expect(screen.getByTestId("mode").textContent).toBe("dark");
  });

  it("localStorageの保存値を起点に明示選択済みと判定した場合もOS設定のchangeイベントに追従しない", () => {
    window.localStorage.setItem(STORAGE_KEY, "dark");
    const { mql, emitChange } = createMatchMediaMock(false);
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue(mql));

    render(
      <ThemeModeProvider>
        <Probe />
      </ThemeModeProvider>,
    );

    expect(screen.getByTestId("mode").textContent).toBe("dark");

    act(() => {
      emitChange(false);
    });

    expect(screen.getByTestId("mode").textContent).toBe("dark");
  });

  it("Provider外でuseThemeMode()を呼ぶとエラーになる", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Probe />)).toThrow("useThemeMode must be used within ThemeModeProvider");
    consoleErrorSpy.mockRestore();
  });
});
