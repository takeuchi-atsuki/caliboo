import { Link } from "react-router-dom";
import Box from "@mui/material/Box";

import { Mascot } from "../../components/mascot/Mascot";
import { DonutProgress } from "../../components/progress/DonutProgress";
import { Tag } from "../../components/badge/Tag";
import { ShortcutCard } from "../../components/card/ShortcutCard";
import { PageContainer } from "../../components/layout/PageContainer";
import { useHomeSummary } from "./useHomeSummary";

export function HomePage() {
  const { summary, error } = useHomeSummary();

  if (error) {
    return (
      <PageContainer>
        <div style={{ padding: 36 }}>データの取得に失敗しました: {error}</div>
      </PageContainer>
    );
  }

  if (!summary) {
    return (
      <PageContainer>
        <div style={{ padding: 36 }}>読み込み中…</div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div style={{ padding: "30px 36px", display: "flex", flexDirection: "column", gap: 24 }}>
        <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: "24px", alignItems: "stretch" }}>
          <Box
            sx={{
              flex: { xs: "1 1 auto", md: "618 1 0%" },
              background: "linear-gradient(120deg,var(--color-pink-100),var(--color-blue-100))",
              borderRadius: "26px",
              padding: "30px 32px",
              display: "flex",
              gap: "24px",
              alignItems: "center",
              overflow: "hidden",
            }}
          >
            <Mascot size={118} color="var(--color-green-300)" mood="happy" />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, fontSize: 13, color: "var(--color-text-sub)" }}>今日も一日頑張ろう</div>
              <div style={{ fontWeight: 800, fontSize: 27, lineHeight: 1.3, color: "var(--color-text)", margin: "4px 0 6px" }}>
                {summary.hero.message}
              </div>
              <div style={{ fontWeight: 600, fontSize: 13, color: "var(--color-text-sub2)", marginBottom: 18 }}>
                3分でOK。Calibooが一緒に整理するよ。
              </div>
              <Link
                to="/report"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 9,
                  padding: "13px 24px",
                  background: "var(--color-pink-400)",
                  borderRadius: 16,
                  fontWeight: 800,
                  fontSize: 15,
                  color: "var(--color-panel)",
                  textDecoration: "none",
                  boxShadow: "0 10px 22px color-mix(in srgb, var(--color-pink-400) 40%, transparent)",
                }}
              >
                <i className="ph-bold ph-note-pencil" style={{ fontSize: 19 }} />
                日報を書く
              </Link>
            </div>
          </Box>
          <Box
            sx={{
              flex: { xs: "1 1 auto", md: "382 1 0%" },
              background: "var(--color-panel)",
              borderRadius: "26px",
              padding: "26px",
              boxShadow: "0 6px 20px var(--color-border-soft)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "10px",
            }}
          >
            <DonutProgress
              percent={summary.certification.achievementPercent}
              size={138}
              color="var(--color-green-400)"
              trackColor="var(--color-green-100)"
              label={`${summary.certification.achievementPercent}%`}
              subLabel={summary.certification.name}
            />
            <div style={{ fontWeight: 600, fontSize: 12.5, color: "var(--color-text-sub2)" }}>
              資格取得まであと少し！
            </div>
          </Box>
        </Box>

        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontWeight: 600, fontSize: 12, color: "var(--color-text-sub)", display: "flex", alignItems: "center", gap: 6 }}>
            <i className="ph-fill ph-sparkle" style={{ color: "var(--color-purple-400)" }} />
            今のあなたの強み
          </span>
          {summary.strengths.map((strength) => (
            <Tag key={strength.label} label={strength.label} tone={strength.tone} />
          ))}
        </div>

        <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: "20px" }}>
          {summary.shortcuts.map((shortcut) => (
            <ShortcutCard key={shortcut.to} {...shortcut} />
          ))}
        </Box>
      </div>
    </PageContainer>
  );
}
