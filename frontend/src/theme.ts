import { createTheme } from "@mui/material/styles";

/**
 * !NOTE: 色・角丸の実値は`src/styles/tokens.css`のCSS変数を単一のソースとして参照する。
 *        ここに16進カラーコードを再定義すると、tokens.cssとの二重管理になり
 *        変更漏れの原因になるため、独自キー(`accent`)は必ず`var(--color-*)`経由で渡す。
 * !WARNING: `palette.text`/`palette.background`はMUIコンポーネント内部が
 *           `alpha()`/`darken()`等の色演算(@mui/system/colorManipulator)に使うため、
 *           `var(--color-*)`のようなCSS変数参照を渡すと"Unsupported color"エラーになる。
 *           このため両者だけは例外的にtokens.cssの値をハードコード転記している
 *           (tokens.css変更時はここも合わせて更新が必要)。ダークモード対応により
 *           この2つだけは`mode`引数で値を出し分ける関数(`createAppTheme`)にしている。
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
        default: isDark ? "#201e29" : "#faf6f1",
        paper: isDark ? "#322f3d" : "#ffffff",
      },
      text: {
        primary: isDark ? "#f1eef7" : "#5b5364",
        secondary: isDark ? "#9c93ab" : "#a89fb0",
      },
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
      fontFamily: "'M PLUS Rounded 1c', system-ui, sans-serif",
    },
    breakpoints: {
      values: { xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536 },
    },
  });
}
