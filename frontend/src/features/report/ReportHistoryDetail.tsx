import { MOOD_OPTIONS } from "../../lib/moodOptions";
import { KPT_SECTIONS } from "../../lib/kptSections";
import type { ReportHistoryItem } from "../../lib/types";

export interface ReportHistoryDetailProps {
  item: ReportHistoryItem;
}

export function ReportHistoryDetail({ item }: ReportHistoryDetailProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {KPT_SECTIONS.map((section) => (
        <div key={section.key} style={{ background: section.bgColor, borderRadius: 13, padding: 13 }}>
          <div style={{ fontWeight: 800, fontSize: 13, color: section.labelColor, marginBottom: 6 }}>
            {section.label}
          </div>
          <div style={{ fontWeight: 500, fontSize: 13, color: "var(--color-text)", whiteSpace: "pre-wrap" }}>
            {item[section.key] || "—"}
          </div>
        </div>
      ))}

      <div style={{ background: "var(--color-orange-200)", borderRadius: 13, padding: 13 }}>
        <div style={{ fontWeight: 800, fontSize: 13, color: "var(--color-orange-600)", marginBottom: 8 }}>今日感じたこと</div>
        {item.mood.length === 0 ? (
          <span style={{ color: "var(--color-text-sub)", fontSize: 13 }}>—</span>
        ) : (
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: item.moodComment ? 8 : 0 }}>
            {item.mood.map((mood) => {
              const option = MOOD_OPTIONS.find((o) => o.value === mood);
              if (!option) return null;
              return (
                <span
                  key={mood}
                  style={{
                    background: option.bg,
                    color: option.fg,
                    padding: "4px 12px",
                    borderRadius: 12,
                    fontWeight: 700,
                    fontSize: 12,
                  }}
                >
                  {option.label}
                </span>
              );
            })}
          </div>
        )}
        {item.moodComment ? (
          <div style={{ fontWeight: 500, fontSize: 13, color: "var(--color-text)", whiteSpace: "pre-wrap" }}>
            {item.moodComment}
          </div>
        ) : null}
      </div>
    </div>
  );
}
