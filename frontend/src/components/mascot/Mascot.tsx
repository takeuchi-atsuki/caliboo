export type MascotMood = "cheer" | "happy";

export interface MascotProps {
  size: number;
  color?: string;
  mood?: MascotMood;
  says?: string;
  className?: string;
}

/**
 * Caliboo のマスコットキャラクター。
 * !NOTE: Claude Design の Mascot.dc.html (div + 絶対配置のみで構成) を
 *        そのままReactに移植したもの。size(px)を基準に各パーツを%指定している。
 */
export function Mascot({ size, color = "var(--color-green-300)", mood = "happy", says, className }: MascotProps) {
  const isCheer = mood === "cheer";

  return (
    <div
      className={className}
      style={{ position: "relative", display: "inline-flex", flexDirection: "column", alignItems: "center", gap: 8 }}
    >
      {says ? (
        <div
          style={{
            position: "relative",
            background: "var(--color-panel)",
            border: "2px solid var(--color-border-soft)",
            borderRadius: 16,
            padding: "9px 13px",
            font: "600 13px/1.45 'M PLUS Rounded 1c',sans-serif",
            color: "var(--color-text)",
            boxShadow: "0 6px 16px var(--color-border-soft)",
            maxWidth: 230,
            textAlign: "center",
          }}
        >
          {says}
        </div>
      ) : null}
      <div style={{ position: "relative", width: size, height: size }}>
        <div
          style={{
            position: "absolute",
            left: "6%",
            top: "-6%",
            width: "24%",
            height: "34%",
            background: color,
            borderRadius: "50% 50% 40% 40%",
            transform: "rotate(-16deg)",
          }}
        />
        <div
          style={{
            position: "absolute",
            right: "6%",
            top: "-6%",
            width: "24%",
            height: "34%",
            background: color,
            borderRadius: "50% 50% 40% 40%",
            transform: "rotate(16deg)",
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: color,
            borderRadius: "50% 50% 47% 47% / 57% 57% 43% 43%",
            boxShadow: "inset 0 -7px 11px var(--color-border-soft)",
          }}
        />
        {!isCheer ? (
          <>
            <div
              style={{ position: "absolute", top: "42%", left: "29%", width: "13%", height: "15%", background: "var(--color-text)", borderRadius: "50%" }}
            />
            <div
              style={{ position: "absolute", top: "42%", left: "58%", width: "13%", height: "15%", background: "var(--color-text)", borderRadius: "50%" }}
            />
            <div
              style={{ position: "absolute", top: "45%", left: "31%", width: "4%", height: "4%", background: "var(--color-panel)", borderRadius: "50%" }}
            />
            <div
              style={{ position: "absolute", top: "45%", left: "60%", width: "4%", height: "4%", background: "var(--color-panel)", borderRadius: "50%" }}
            />
          </>
        ) : (
          <>
            <div
              style={{
                position: "absolute",
                top: "44%",
                left: "27%",
                width: "16%",
                height: "10%",
                border: "2.5px solid var(--color-text)",
                borderBottom: "none",
                borderRadius: "50% 50% 0 0 / 100% 100% 0 0",
              }}
            />
            <div
              style={{
                position: "absolute",
                top: "44%",
                left: "57%",
                width: "16%",
                height: "10%",
                border: "2.5px solid var(--color-text)",
                borderBottom: "none",
                borderRadius: "50% 50% 0 0 / 100% 100% 0 0",
              }}
            />
          </>
        )}
        <div
          style={{ position: "absolute", top: "55%", left: "17%", width: "14%", height: "9%", background: "color-mix(in srgb, var(--color-pink-400) 50%, transparent)", borderRadius: "50%" }}
        />
        <div
          style={{ position: "absolute", top: "55%", left: "69%", width: "14%", height: "9%", background: "color-mix(in srgb, var(--color-pink-400) 50%, transparent)", borderRadius: "50%" }}
        />
        <div
          style={{
            position: "absolute",
            top: "57%",
            left: "43%",
            width: "13%",
            height: "8%",
            border: "2px solid var(--color-text)",
            borderTop: "none",
            borderRadius: "0 0 60% 60% / 0 0 100% 100%",
          }}
        />
        <div style={{ position: "absolute", top: "-10%", right: "2%", color: "var(--color-orange-500)", fontSize: size * 0.22, lineHeight: 1 }}>
          ✦
        </div>
      </div>
    </div>
  );
}
