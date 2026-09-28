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
      <Box component="main" sx={{ p: "var(--page-gutter)", display: "flex", flexDirection: "column", gap: { xs: 3, md: 4 }, overflowWrap: "anywhere" }}>
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
            {/* !NOTE: 情報の優先順位をDOM順にも反映し、読み上げ・Tab移動を表示順と揃える。 */}
            <Box component="section" aria-labelledby="strengths-title" sx={{ ...panelSx, background: "linear-gradient(115deg, var(--color-purple-100), var(--color-blue-100))", p: { xs: 3, md: 4 }, display: "flex", alignItems: "center", gap: { xs: 2, md: 4 } }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Stack direction="row" spacing={1.5} sx={{ mb: 1.5, alignItems: "center" }}>
                  <Box sx={{ width: 44, height: 44, flexShrink: 0, borderRadius: "14px", bgcolor: "var(--color-panel)", display: "grid", placeItems: "center", color: "var(--color-purple-500)" }}><PhosphorIcon name="ph ph-sparkle" size={24} /></Box>
                  <Typography id="strengths-title" component="h2" sx={{ fontSize: { xs: 23, md: 28 }, fontWeight: 800, letterSpacing: "-0.035em", lineHeight: 1.5 }}>今のあなたの強み</Typography>
                </Stack>
                <Typography variant="body2" color="text.secondary">日々の取り組みから、あなたらしさを発見。</Typography>
                <Box sx={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 1, my: 2.5 }}>
                  {summary.strengths.length === 0 && <Typography variant="body2" color="text.secondary">日報や課題から強みを見つけていきます。</Typography>}
                  {summary.strengths.map((strength) => <Tag key={strength.label} label={strength.label} tone={strength.tone} />)}
                </Box>
                <Button component={Link} to="/strengths" variant="contained" color="secondary" endIcon={<PhosphorIcon name="ph ph-arrow-right" size={18} />} sx={{ minHeight: 48, width: { xs: "100%", sm: "auto" } }}>強みを詳しく見る</Button>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>強みの根拠と、成長のヒントを確認できます。</Typography>
              </Box>
              <Box aria-hidden="true" sx={{ display: { xs: "none", sm: "block" }, flexShrink: 0, transform: "rotate(-7deg)", px: { sm: 1, md: 4 } }}>
                <Mascot size={112} color="var(--color-green-300)" mood="happy" />
              </Box>
            </Box>

            <Box component="section" aria-labelledby="reflection-title" sx={{ ...panelSx, p: { xs: 3, md: 3.5 }, display: "flex", flexDirection: { xs: "column", md: "row" }, alignItems: { xs: "stretch", md: "center" }, gap: 2.5 }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1 }}>
                  <PhosphorIcon name="ph ph-sun-horizon" size={24} color="var(--color-pink-500)" />
                  <Typography id="reflection-title" component="h2" variant="h2">今日のふり返り</Typography>
                </Stack>
                <Typography sx={{ fontWeight: 700 }}>{summary.hero.message}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>3分でOK。Calibooと一緒に、今日の気づきを残そう。</Typography>
              </Box>
              <Button component={Link} to="/report" variant="outlined" color="secondary" startIcon={<PhosphorIcon name="ph ph-note-pencil" size={20} />} sx={{ minHeight: 48, flexShrink: 0, alignSelf: { xs: "stretch", sm: "flex-start", md: "center" } }}>日報を書く</Button>
            </Box>

            <Box component="section" aria-labelledby="shortcuts-title">
              <Typography id="shortcuts-title" component="h2" variant="h2" sx={{ mb: 2 }}>今日は何をしよう？</Typography>
              <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 2 }}>
                {summary.shortcuts.map((shortcut) => <ShortcutCard key={shortcut.to} {...shortcut} />)}
              </Box>
            </Box>

            <Box component="section" aria-labelledby="progress-title" sx={{ ...panelSx, p: { xs: 3, md: 3.5 }, display: "flex", flexDirection: { xs: "column", md: "row" }, alignItems: { xs: "stretch", md: "center" }, gap: 2.5 }}>
              <Box sx={{ display: "flex", flex: 1, alignItems: "center", gap: { xs: 2, md: 3 }, minWidth: 0 }}>
                <Box role="progressbar" aria-labelledby="progress-title" aria-valuenow={summary.certification.achievementPercent} aria-valuemin={0} aria-valuemax={100} sx={{ flexShrink: 0 }}>
                  <DonutProgress percent={summary.certification.achievementPercent} size={88} color="var(--color-green-400)" trackColor="var(--color-green-100)" label={`${summary.certification.achievementPercent}%`} subLabel="達成率" />
                </Box>
                <Box sx={{ minWidth: 0 }}>
                  <Typography id="progress-title" component="h2" sx={{ fontSize: { xs: 16, md: 18 }, fontWeight: 700 }}>{summary.certification.name}の学習度</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>自分のペースで、少しずつ積み重ねよう。</Typography>
                </Box>
              </Box>
              <Button component={Link} to="/study" endIcon={<PhosphorIcon name="ph ph-arrow-right" size={18} />} sx={{ flexShrink: 0, alignSelf: { xs: "stretch", sm: "flex-start", md: "center" } }}>学習を続ける</Button>
            </Box>
          </>
        )}
      </Box>
    </PageContainer>
  );
}
