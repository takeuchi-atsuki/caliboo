import { createTheme } from "@mui/material/styles";

/**
 * !NOTE: 色・角丸の実値は`src/styles/tokens.css`のCSS変数を単一のソースとして参照する。
 *        ここに16進カラーコードを再定義すると、tokens.cssとの二重管理になり
 *        変更漏れの原因になるため、独自キー(`accent`)は必ず`var(--color-*)`経由で渡す。
 * !WARNING: `palette.text`/`palette.background`はMUIコンポーネント内部が
 *           `alpha()`/`darken()`等の色演算(@mui/system/colorManipulator)に使うため、
 *           `var(--color-*)`のようなCSS変数参照を渡すと"Unsupported color"エラーになる。
 *           このためこれらとprimary/secondaryはtokens.cssの実値を転記している
 *           (tokens.css変更時はここも合わせて更新が必要)。ダークモード対応により
 *           これらは`mode`引数で値を出し分ける関数(`createAppTheme`)にしている。
 *           `accent`は`var(--color-*)`のままで済むため、mode分岐は不要
 *           (`[data-theme="dark"]`側でCSS変数の値自体が切り替わるため)。
 */

export interface AccentTone {
  main: string;
  light: string;
  wash: string;
  contrastText: string;
}

declare module "@mui/material/styles" {
  interface Palette {
    accent: {
      green: AccentTone;
      blue: AccentTone;
      purple: AccentTone;
      pink: AccentTone;
      orange: AccentTone;
    };
  }
  interface PaletteOptions {
    accent?: {
      green: AccentTone;
      blue: AccentTone;
      purple: AccentTone;
      pink: AccentTone;
      orange: AccentTone;
    };
  }
  interface Theme {
    radius: { lg: string; md: string; sm: string };
  }
  interface ThemeOptions {
    radius?: { lg: string; md: string; sm: string };
  }
}

export const NUMERIC_FONT_FAMILY = "'Nunito', system-ui, sans-serif";

export type ThemeMode = "light" | "dark";

export function createAppTheme(mode: ThemeMode) {
  const isDark = mode === "dark";
  return createTheme({
    palette: {
      mode,
      background: {
        default: isDark ? "#1b1c24" : "#f7f7fa",
        paper: isDark ? "#252630" : "#ffffff",
      },
      text: {
        primary: isDark ? "#f1eef7" : "#303342",
        secondary: isDark ? "#b1adbf" : "#6b6e7e",
      },
      primary: { main: isDark ? "#85d8bb" : "#327963", contrastText: isDark ? "#192d29" : "#ffffff" },
      secondary: { main: isDark ? "#b6a8f2" : "#6b58a8" },
      divider: isDark ? "rgba(255,255,255,0.12)" : "rgba(48,51,66,0.12)",
      accent: {
        green: {
          main: "var(--color-green-500)",
          light: "var(--color-green-200)",
          wash: "var(--color-green-100)",
          contrastText: "#fff",
        },
        blue: {
          main: "var(--color-blue-500)",
          light: "var(--color-blue-200)",
          wash: "var(--color-blue-100)",
          contrastText: "#fff",
        },
        purple: {
          main: "var(--color-purple-500)",
          light: "var(--color-purple-200)",
          wash: "var(--color-purple-100)",
          contrastText: "#fff",
        },
        pink: {
          main: "var(--color-pink-500)",
          light: "var(--color-pink-200)",
          wash: "var(--color-pink-100)",
          contrastText: "#fff",
        },
        orange: {
          main: "var(--color-orange-600)",
          light: "var(--color-orange-200)",
          wash: "var(--color-orange-100)",
          contrastText: "#fff",
        },
      },
    },
    radius: {
      lg: "var(--radius-lg)",
      md: "var(--radius-md)",
      sm: "var(--radius-sm)",
    },
    shape: {
      borderRadius: 16,
    },
    typography: {
      fontFamily: "var(--font-body)",
      h1: { fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.04em" },
      h2: { fontSize: "1.35rem", fontWeight: 700, letterSpacing: "-0.02em" },
      h5: { fontSize: "1.65rem", fontWeight: 800, letterSpacing: "-0.03em" },
      h6: { fontSize: "1.1rem", fontWeight: 700 },
      body1: { fontSize: "0.9375rem", lineHeight: 1.75 },
      body2: { lineHeight: 1.7 },
      button: { fontWeight: 700, textTransform: "none" },
    },
    components: {
      MuiButtonBase: {
        styleOverrides: {
          root: { "&.Mui-focusVisible": { outline: "3px solid var(--color-action)", outlineOffset: 3 } },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { minHeight: 44, borderRadius: 14, padding: "10px 18px", transition: "background-color .16s, box-shadow .16s" },
        },
      },
      MuiIconButton: { styleOverrides: { root: { minWidth: 44, minHeight: 44, borderRadius: 14 } } },
      MuiPaper: { styleOverrides: { root: { backgroundImage: "none" }, elevation1: { boxShadow: "var(--shadow-card)", border: "1px solid var(--color-border-soft)" } } },
      MuiOutlinedInput: { styleOverrides: { root: { borderRadius: 14, background: "var(--color-panel)" }, notchedOutline: { borderColor: "var(--color-border)" } } },
      MuiInputBase: { styleOverrides: { root: { "&.Mui-focused": { outline: "2px solid var(--color-action)", outlineOffset: 2 } }, input: { "&::placeholder": { color: "var(--color-text-sub)", opacity: 1 } } } },
      MuiDialog: { styleOverrides: { paper: { borderRadius: 24, boxShadow: "var(--shadow-float)" } } },
      MuiDrawer: { styleOverrides: { paper: { backgroundImage: "none" } } },
      MuiAlert: { styleOverrides: { root: { borderRadius: 16, alignItems: "center" } } },
      MuiTableCell: { styleOverrides: { root: { borderColor: "var(--color-border-soft)", padding: "16px" }, head: { background: "var(--color-bg)", color: "var(--color-text-sub2)", fontWeight: 700 } } },
      MuiTabs: { styleOverrides: { root: { minHeight: 48 }, indicator: { height: 3, borderRadius: 3 } } },
      MuiTab: { styleOverrides: { root: { textTransform: "none", minHeight: 48, fontWeight: 700 } } },
    },
    breakpoints: {
      values: { xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536 },
    },
  });
}
