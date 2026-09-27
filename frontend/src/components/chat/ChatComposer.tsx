import InputBase from "@mui/material/InputBase";
import IconButton from "@mui/material/IconButton";
import Box from "@mui/material/Box";

import { PhosphorIcon } from "../icon/PhosphorIcon";

export interface ChatComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  placeholder?: string;
  accentColor?: string;
}

/**
 * !NOTE: ラベル領域を持たない`InputBase`を使い、`TextField`の未使用ラベル分の
 *        余白を持たせない構成にしている(Textarea.tsxと同じ理由)。送信も
 *        `<form onSubmit>`ではなくEnterキー押下・ボタンクリックの直接呼び出しに
 *        しており、これは移行前の実装と同一の挙動。
 * !NOTE: 日本語入力の変換確定のEnterで誤送信しないよう、IME変換中(`isComposing`)の
 *        Enterは送信しない。Safariは変換確定のkeydownを`compositionend`の後に
 *        `isComposing=false`で発火させるため、変換中を示す`keyCode === 229`も併せて判定する
 *        (`keyCode`は非推奨だが、この判定に代わる標準APIが無い)。
 */
export function ChatComposer({
  value,
  onChange,
  onSend,
  placeholder = "メッセージを入力…",
  accentColor = "var(--color-blue-400)",
}: ChatComposerProps) {
  return (
    <Box sx={{ display: "flex", gap: "11px", alignItems: "center" }}>
      <InputBase
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key !== "Enter" || e.nativeEvent.isComposing || e.keyCode === 229) return;
          if (value.trim()) onSend();
        }}
        placeholder={placeholder}
        fullWidth
        sx={{
          flex: 1,
          border: "1.5px solid var(--color-border)",
          background: "var(--color-bg)",
          borderRadius: "15px",
          padding: "14px 17px",
          font: "500 14px 'M PLUS Rounded 1c'",
          color: "var(--color-text)",
        }}
      />
      <IconButton
        onClick={() => value.trim() && onSend()}
        aria-label="送信"
        sx={{
          width: 48,
          height: 48,
          flex: "none",
          borderRadius: "15px",
          background: accentColor,
          boxShadow: `0 8px 18px color-mix(in srgb, ${accentColor} 40%, transparent)`,
          "&:hover": { background: accentColor },
        }}
      >
        <PhosphorIcon name="ph-fill ph-paper-plane-tilt" color="var(--color-panel)" size={20} />
      </IconButton>
    </Box>
  );
}
