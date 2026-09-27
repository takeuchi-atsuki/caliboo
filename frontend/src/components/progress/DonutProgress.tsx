export interface DonutProgressProps {
  percent: number;
  size?: number;
  color?: string;
  trackColor?: string;
  label: string;
  subLabel?: string;
}

export function DonutProgress({
  percent,
  size = 104,
  color = "var(--color-green-400)",
  trackColor = "var(--color-green-100)",
  label,
  subLabel,
}: DonutProgressProps) {
  const inner = size * 0.75;
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: `conic-gradient(${color} 0 ${percent}%, ${trackColor} ${percent}% 100%)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: inner,
          height: inner,
          borderRadius: "50%",
          background: "var(--color-panel)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span className="font-numeric" style={{ fontWeight: 800, fontSize: size * 0.22, color: "var(--color-text)" }}>
          {label}
        </span>
        {subLabel ? (
          <span style={{ fontWeight: 600, fontSize: size * 0.09, color: "var(--color-text-sub)" }}>
            {subLabel}
          </span>
        ) : null}
      </div>
    </div>
  );
}
