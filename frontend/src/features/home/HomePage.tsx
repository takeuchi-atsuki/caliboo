import { Link } from "react-router-dom";
import { Alert, Box, Button, Skeleton, Stack, Typography } from "@mui/material";

import { Mascot } from "../../components/mascot/Mascot";
import { DonutProgress } from "../../components/progress/DonutProgress";
import { Tag } from "../../components/badge/Tag";
import { ShortcutCard } from "../../components/card/ShortcutCard";
import { PageContainer } from "../../components/layout/PageContainer";
import { PhosphorIcon } from "../../components/icon/PhosphorIcon";
import { useHomeSummary } from "./useHomeSummary";

const panelSx = { borderRadius: "var(--radius-lg)", border: "1px solid var(--color-border-soft)", boxShadow: "var(--shadow-card)", bgcolor: "var(--color-panel)" };

export function HomePage() {
  const { summary, error } = useHomeSummary();

  return (
    <PageContainer>
      <Box component="main" sx={{ p: "var(--page-gutter)", display: "flex", flexDirection: "column", gap: { xs: 3, md: 4 } }}>
        <Box component="header">
          <Typography component="h1" variant="h1" sx={{ mb: 0.75 }}>ホーム</Typography>
          <Typography color="text.secondary" variant="body2">今日も、自分のペースで。一歩ずつ進めていこう。</Typography>
        </Box>

        {error ? (
          <Alert severity="error">データの取得に失敗しました: {error}</Alert>
        ) : !summary ? (
          <Box role="status" aria-label="ホームを読み込み中">
            <Typography color="text.secondary" sx={{ mb: 2 }}>読み込み中…</Typography>
            <Skeleton variant="rounded" height={260} sx={{ borderRadius: "var(--radius-lg)", mb: 3 }} />
            <Skeleton variant="rounded" height={120} sx={{ borderRadius: "var(--radius-lg)" }} />
          </Box>
        ) : (
          <>
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(0, 1.65fr) minmax(0, 1fr)" }, gap: 3 }}>
              <Box component="section" aria-labelledby="reflection-title" sx={{ ...panelSx, background: "linear-gradient(115deg, var(--color-pink-100), var(--color-purple-100) 65%, var(--color-blue-100))", p: { xs: 3, md: 4 }, position: "relative", overflow: "hidden", display: "flex", alignItems: "center", gap: 2 }}>
                <Box sx={{ flex: 1, minWidth: 0, position: "relative", zIndex: 1 }}>
                  <Box sx={{ display: "inline-flex", alignItems: "center", gap: 0.75, color: "var(--color-pink-500)", fontWeight: 700, fontSize: 12, mb: 2 }}>
                    <PhosphorIcon name="ph ph-sun-horizon" size={18} />今日の振り返り
                  </Box>
                  <Typography id="reflection-title" component="h2" sx={{ fontSize: { xs: 23, md: 28 }, fontWeight: 800, letterSpacing: "-0.035em", lineHeight: 1.55, maxWidth: 430 }}>{summary.hero.message}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 3 }}>3分でOK。Calibooと一緒に、今日の気づきを残そう。</Typography>
                  <Button component={Link} to="/report" variant="contained" startIcon={<PhosphorIcon name="ph ph-note-pencil" size={20} />}
                    sx={{ px: 3, minHeight: 48, bgcolor: "var(--color-pink-500)", color: "var(--color-panel)", "&:hover": { bgcolor: "var(--color-pink-500)", filter: "brightness(.95)" } }}>
                    日報を書く
                  </Button>
                </Box>
                <Box aria-hidden="true" sx={{ position: { xs: "absolute", sm: "relative" }, top: { xs: 20, sm: "auto" }, right: { xs: 20, sm: "auto" }, flexShrink: 0 }}>
                  <Box sx={{ display: { xs: "block", sm: "none" } }}><Mascot size={48} color="var(--color-green-300)" mood="happy" /></Box>
                  <Box sx={{ display: { xs: "none", sm: "block" }, transform: "rotate(-7deg)", p: 1 }}><Mascot size={112} color="var(--color-green-300)" mood="happy" /></Box>
                </Box>
              </Box>

              <Box component="section" aria-labelledby="progress-title" sx={{ ...panelSx, p: 3, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 1.5 }}>
                <Typography id="progress-title" component="h2" sx={{ fontSize: 14, fontWeight: 700, alignSelf: "flex-start" }}>学びの積み重ね</Typography>
                <Box sx={{ display: "flex", flexDirection: { xs: "row", md: "column" }, alignItems: "center", gap: { xs: 2, md: 1.5 }, width: "100%" }}>
                  <Box sx={{ flexShrink: 0 }}><DonutProgress percent={summary.certification.achievementPercent} size={112} color="var(--color-green-400)" trackColor="var(--color-green-100)" label={`${summary.certification.achievementPercent}%`} subLabel="達成率" /></Box>
                  <Box sx={{ textAlign: { xs: "left", md: "center" }, minWidth: 0 }}>
                    <Typography sx={{ fontSize: 14, fontWeight: 700 }}>{summary.certification.name}</Typography>
                    <Button component={Link} to="/study" endIcon={<PhosphorIcon name="ph ph-arrow-right" size={16} />} sx={{ fontSize: 13, px: 0.5, mt: 0.5 }}>学習を続ける</Button>
                  </Box>
                </Box>
              </Box>
            </Box>

            <Box component="section" aria-labelledby="shortcuts-title">
              <Typography id="shortcuts-title" component="h2" variant="h2" sx={{ mb: 2 }}>今日は何をしよう？</Typography>
              <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 2 }}>
                {summary.shortcuts.map((shortcut) => <ShortcutCard key={shortcut.to} {...shortcut} />)}
              </Box>
            </Box>

            <Box component="section" aria-labelledby="strengths-title" sx={{ ...panelSx, p: { xs: 3, md: 3.5 } }}>
              <Stack direction="row" spacing={1.5} sx={{ mb: 2, alignItems: "center" }}>
                <Box sx={{ width: 44, height: 44, borderRadius: "14px", bgcolor: "var(--color-purple-100)", display: "grid", placeItems: "center", color: "var(--color-purple-500)" }}><PhosphorIcon name="ph ph-sparkle" size={24} /></Box>
                <Box>
                  <Typography id="strengths-title" component="h2" sx={{ fontSize: 17, fontWeight: 700 }}>今のあなたの強み</Typography>
                  <Typography variant="body2" color="text.secondary">日々の取り組みから、あなたらしさを発見。</Typography>
                </Box>
              </Stack>
              <Box sx={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 1, mb: 1 }}>
                {summary.strengths.length === 0 && <Typography variant="body2" color="text.secondary">日報や課題から強みを見つけていきます。</Typography>}
                {summary.strengths.map((strength) => <Tag key={strength.label} label={strength.label} tone={strength.tone} />)}
              </Box>
              <Button component={Link} to="/strengths" color="secondary" endIcon={<PhosphorIcon name="ph ph-arrow-right" size={16} />} sx={{ px: 0.5, fontSize: 13 }}>根拠と成長のヒントを見る</Button>
            </Box>
          </>
        )}
      </Box>
    </PageContainer>
  );
}
