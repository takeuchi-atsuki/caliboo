import { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

import { Mascot } from "../../components/mascot/Mascot";
import { PageContainer } from "../../components/layout/PageContainer";
import { Button } from "../../components/ui/Button";
import { Tag } from "../../components/badge/Tag";
import { overallStatusLabel } from "../../lib/strengthStatus";
import type { StrengthItem } from "../../lib/types";
import { useStrengthsPoc } from "./useStrengthsPoc";
import { StrengthCard } from "./StrengthCard";
import { StrengthEvidenceDialog } from "./StrengthEvidenceDialog";
import { RunTrajectoryView } from "./RunTrajectoryView";

export function StrengthsPage() {
  const {
    personas,
    selectedPersonaKey,
    setSelectedPersonaKey,
    runs,
    detail,
    running,
    notice,
    setNotice,
    startRun,
    selectRun,
  } = useStrengthsPoc();
  const [openedStrength, setOpenedStrength] = useState<StrengthItem | null>(null);
  const selectedPersona = personas.find((persona) => persona.personaKey === selectedPersonaKey);

  return (
    <PageContainer>
      <div style={{ padding: "var(--page-gutter)", display: "flex", flexDirection: "column", gap: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Mascot size={46} color="var(--color-purple-200)" mood="happy" />
          <div>
            <div style={{ fontWeight: 800, fontSize: 23, color: "var(--color-text)" }}>強み解析（PoC）</div>
            <div style={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>
              OJTの作業ログ・日報・レビューから強みを解析します
            </div>
          </div>
        </div>

        <Alert severity="info" icon={false} sx={{ borderRadius: "14px" }}>
          ここで生成される強みは<strong>育成支援を目的</strong>としたものであり、査定・選別には使用しません。
        </Alert>

        {notice ? (
          <Alert severity={notice.severity} onClose={() => setNotice(null)}>
            {notice.message}
          </Alert>
        ) : null}

        <Box
          sx={{
            background: "var(--color-panel)",
            borderRadius: "20px",
            padding: "20px 22px",
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            gap: "14px",
            alignItems: { xs: "stretch", md: "flex-end" },
          }}
        >
          <TextField
            select
            size="small"
            label="デモシナリオ"
            value={selectedPersonaKey}
            onChange={(event) => setSelectedPersonaKey(event.target.value)}
            sx={{ flex: 1 }}
          >
            {personas.map((persona) => (
              <MenuItem key={persona.personaKey} value={persona.personaKey}>
                {persona.label}
              </MenuItem>
            ))}
          </TextField>
          <Button
            icon="ph-bold ph-play"
            accentColor="var(--color-purple-400)"
            onClick={startRun}
            disabled={running || !selectedPersonaKey}
          >
            {running ? "解析中…" : "解析を実行"}
          </Button>
        </Box>

        {selectedPersona ? (
          <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)", marginTop: "-10px" }}>
            {selectedPersona.description}
          </Box>
        ) : null}

        {runs.length > 0 ? (
          <Box sx={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            <Box component="span" sx={{ fontWeight: 600, fontSize: 12, color: "var(--color-text-sub)" }}>
              実行履歴
            </Box>
            {runs.map((run) => (
              <Box
                key={run.id}
                component="button"
                onClick={() => selectRun(run.id)}
                sx={{
                  padding: "7px 14px",
                  borderRadius: "16px",
                  fontWeight: 700,
                  fontSize: 12,
                  cursor: "pointer",
                  border: "1px solid var(--color-border)",
                  background: detail?.id === run.id ? "var(--color-purple-100)" : "var(--color-panel)",
                  color: detail?.id === run.id ? "var(--color-purple-500)" : "var(--color-text-sub)",
                }}
              >
                {run.id}：{run.label}
              </Box>
            ))}
          </Box>
        ) : null}

        {detail ? (
          <>
            <Box
              sx={{
                background: "var(--color-panel)",
                borderRadius: "20px",
                padding: "18px 22px",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <Box sx={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
                <Box component="span" sx={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)" }}>
                  {detail.label}（{detail.subjectId}）
                </Box>
                <Tag label={overallStatusLabel(detail.strengths.overallStatus)} tone="blue" />
              </Box>
              {detail.injectedPersona ? (
                <Box sx={{ fontWeight: 500, fontSize: 12, color: "var(--color-text-sub2)" }}>
                  注入ペルソナ（検証用の既知の強み）：{detail.injectedPersona}
                </Box>
              ) : null}
              <Box sx={{ fontWeight: 500, fontSize: 12, color: "var(--color-text-sub)" }}>
                {detail.strengths.notes}
              </Box>
              <Box sx={{ fontWeight: 500, fontSize: 11.5, color: "var(--color-text-sub2)" }}>
                生成：{detail.trace.generationProvider} ／ 解析：{detail.trace.analysisProvider} ／
                {detail.trace.scriptVersion
                  ? `台本：${detail.trace.scriptVersion}`
                  : `エージェント：${detail.trace.agents?.length ?? 0}件`}
              </Box>
            </Box>

            {detail.trace.externalAnalysis && <Box sx={{ p: 2, background: "var(--color-panel)", overflowX: "auto" }}>
              <h2>独立エージェントとの比較</h2>
              <table><thead><tr><th>スキル</th><th>ルールベース</th><th>独立解析</th></tr></thead><tbody>
                {[...new Set([...detail.strengths.strengths, ...detail.trace.externalAnalysis.strengths].map((item) => item.layerTask.skillCode))].map((code) => {
                  const rule = detail.strengths.strengths.find((item) => item.layerTask.skillCode === code);
                  const agent = detail.trace.externalAnalysis?.strengths.find((item) => item.layerTask.skillCode === code);
                  return <tr key={code}><th>{code}</th><td>{rule ? `${rule.status} (${rule.confidence})` : "なし"}</td><td>{agent ? `${agent.status} (${agent.confidence})` : "なし"}</td></tr>;
                })}
              </tbody></table>
              <p>{detail.trace.externalAnalysis.notes}</p>
            </Box>}
            {detail.strengths.strengths.length > 0 ? (
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                  gap: "16px",
                }}
              >
                {detail.strengths.strengths.map((strength) => (
                  <StrengthCard
                    key={strength.id}
                    strength={strength}
                    onOpenEvidence={setOpenedStrength}
                  />
                ))}
              </Box>
            ) : (
              <Box
                sx={{
                  background: "var(--color-panel)",
                  borderRadius: "20px",
                  padding: "26px",
                  textAlign: "center",
                  fontWeight: 600,
                  fontSize: 13,
                  color: "var(--color-text-sub)",
                }}
              >
                根拠が十分な強みは見つかりませんでした。断定せず評価保留としています。
              </Box>
            )}

            <RunTrajectoryView detail={detail} />
          </>
        ) : null}
      </div>

      <StrengthEvidenceDialog strength={openedStrength} onClose={() => setOpenedStrength(null)} />
    </PageContainer>
  );
}
