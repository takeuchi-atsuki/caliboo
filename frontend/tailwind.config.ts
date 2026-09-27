// !NOTE: Tailwind CSS撤去(MUI移行 Phase 7)により、このファイルはもう
//        ビルドから参照されていない(postcss.config.jsからプラグイン登録を削除済み)。
//        `tailwindcss`パッケージ自体もpackage.jsonから削除したため、このファイルを
//        今後編集しても効果はない。削除してよいが、削除コマンドの実行権限上の理由で
//        参照用にファイルのみ残している。
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        "bg-alt": "var(--color-bg-alt)",
        panel: "var(--color-panel)",
        ink: "var(--color-text)",
        "ink-sub": "var(--color-text-sub)",
        "ink-sub2": "var(--color-text-sub2)",
        border: "var(--color-border)",
        "border-soft": "var(--color-border-soft)",
        green: {
          200: "var(--color-green-200)",
          300: "var(--color-green-300)",
          400: "var(--color-green-400)",
          500: "var(--color-green-500)",
        },
        blue: {
          200: "var(--color-blue-200)",
          400: "var(--color-blue-400)",
          500: "var(--color-blue-500)",
        },
        purple: {
          200: "var(--color-purple-200)",
          400: "var(--color-purple-400)",
          500: "var(--color-purple-500)",
        },
        pink: {
          200: "var(--color-pink-200)",
          300: "var(--color-pink-300)",
          400: "var(--color-pink-400)",
          500: "var(--color-pink-500)",
        },
        orange: {
          200: "var(--color-orange-200)",
          400: "var(--color-orange-400)",
          500: "var(--color-orange-500)",
        },
      },
      borderRadius: {
        lg: "var(--radius-lg)",
        md: "var(--radius-md)",
        sm: "var(--radius-sm)",
      },
      fontFamily: {
        heading: ["'M PLUS Rounded 1c'", "system-ui", "sans-serif"],
        numeric: ["'Nunito'", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
