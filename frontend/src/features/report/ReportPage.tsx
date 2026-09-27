import { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";

import { Mascot } from "../../components/mascot/Mascot";
import { PageContainer } from "../../components/layout/PageContainer";
import { Button } from "../../components/ui/Button";
import { Textarea } from "../../components/ui/Textarea";
import { Dialog } from "../../components/ui/Dialog";
import { MoodPicker } from "../../components/mood/MoodPicker";
import { useAuth } from "../../components/auth/AuthProvider";
import { useReportForm } from "./useReportForm";
import { ReportHistoryTable } from "./ReportHistoryTable";
import { ReportHistoryDetail } from "./ReportHistoryDetail";
import { ReportDraftList } from "./ReportDraftList";
import type { ReportHistoryItem } from "../../lib/types";
import { KPT_SECTIONS } from "../../lib/kptSections";

export function ReportPage() {
  const { user } = useAuth();
  const {
    keep,
    setKeep,
    problem,
    setProblem,
    tryText,
    setTryText,
    mood,
    setMood,
    moodComment,
    setMoodComment,
    feedback,
    setFeedback,
    submitting,
    submit,
    history,
    drafts,
    draftDate,
    fetchDrafts,
    loadDraft,
    clearDraft,
    deleteDraft,
    pendingRestore,
    restoreAutosave,
    discardAutosave,
  } = useReportForm(user?.id ?? 0);

  const [selectedItem, setSelectedItem] = useState<ReportHistoryItem | null>(null);
  const [draftListOpen, setDraftListOpen] = useState(false);

  // !NOTE: RequireAuthが未ログイン中はこのページ自体を描画しないため、通常は必ずuserが
  //        存在する。型を絞り込むためのガードで、実際に到達することは想定していない。
  if (!user) {
    return null;
  }

  const valueByKey: Record<string, string> = { keep, problem, try: tryText };
  const setterByKey: Record<string, (v: string) => void> = {
    keep: setKeep,
    problem: setProblem,
    try: setTryText,
  };

  return (
    <PageContainer>
      <div style={{ padding: "var(--page-gutter)", display: "flex", flexDirection: "column", gap: 24 }}>
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            justifyContent: "space-between",
            alignItems: { xs: "flex-start", sm: "center" },
            gap: "14px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <Mascot size={46} color="var(--color-green-300)" mood="happy" />
            <div>
              <h1 style={{ margin: 0, fontWeight: 800, fontSize: 28, letterSpacing: "-0.03em", color: "var(--color-text)" }}>今日の日報</h1>
              <div style={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)" }}>
                {draftDate ? (
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    編集中の下書き：{draftDate}
                    <span
                      onClick={clearDraft}
                      style={{ color: "var(--color-purple-500)", fontWeight: 700, cursor: "pointer" }}
                    >
                      新規作成に戻す
                    </span>
                  </span>
                ) : (
                  "3つだけ振り返ろう"
                )}
              </div>
            </div>
          </div>
          <Box sx={{ display: "flex", gap: "10px", flexWrap: "wrap", width: { xs: "100%", sm: "auto" }, "& > button": { flex: { xs: "1 1 auto", sm: "0 0 auto" } } }}>
            <Button
              variant="secondary"
              disabled={submitting}
              onClick={() => {
                fetchDrafts();
                setDraftListOpen(true);
              }}
            >
              保存した下書き
            </Button>
            <Button variant="secondary" disabled={submitting} onClick={() => submit("draft")}>
              下書き保存
            </Button>
            <Button icon="ph-bold ph-paper-plane-tilt" disabled={submitting} onClick={() => submit("submitted")}>
              提出する
            </Button>
          </Box>
        </Box>

        {pendingRestore ? (
          <Alert
            severity="info"
            action={
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <Button disabled={submitting} onClick={restoreAutosave}>
                  復元する
                </Button>
                <Button variant="secondary" disabled={submitting} onClick={discardAutosave}>
                  破棄する
                </Button>
              </div>
            }
          >
            前回の入力内容が残っています（{new Date(pendingRestore.savedAt).toLocaleString("ja-JP")}
            {pendingRestore.draftDate ? `・下書き${pendingRestore.draftDate}を編集中` : ""}）。復元しますか？
          </Alert>
        ) : null}

        {feedback ? (
          <Alert severity={feedback.severity} onClose={() => setFeedback(null)}>
            {feedback.message}
          </Alert>
        ) : null}

        <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: "18px" }}>
          {KPT_SECTIONS.map((column) => (
            <Box
              key={column.key}
              sx={{
                flex: { xs: "1 1 auto", md: 1 },
                background: "var(--color-panel)",
                borderRadius: "20px",
                padding: "20px",
                borderTop: `5px solid ${column.accent}`,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 11,
                    background: column.iconBg,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <i className={column.icon} style={{ color: column.iconColor, fontSize: 18 }} />
                </div>
                <span className="font-numeric" style={{ fontWeight: 800, fontSize: 17, color: column.labelColor }}>
                  {column.label}
                </span>
              </div>
              <div style={{ fontWeight: 500, fontSize: 11.5, color: "var(--color-text-sub)", marginBottom: 10 }}>
                {column.description}
              </div>
              <Textarea
                value={valueByKey[column.key]}
                onChange={(e) => setterByKey[column.key](e.target.value)}
                borderColor={column.borderColor}
                bgColor={column.bgColor}
                placeholder={column.placeholder}
              />
            </Box>
          ))}
        </Box>

        <div
          style={{
            background: "var(--color-orange-200)",
            borderRadius: 20,
            padding: "20px 22px",
            border: "1.5px dashed var(--color-orange-100)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <i className="ph-fill ph-heart" style={{ color: "var(--color-orange-500)" }} />
            <span style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)" }}>今日感じたこと</span>
            <span
              style={{
                fontWeight: 500,
                fontSize: 11.5,
                color: "var(--color-orange-600)",
                background: "var(--color-orange-100)",
                padding: "3px 10px",
                borderRadius: 10,
              }}
            >
              ポジ・ネガどっちでもOK / 自由記述
            </span>
          </div>
          <MoodPicker value={mood} onChange={setMood} />
          <textarea
            value={moodComment}
            onChange={(e) => setMoodComment(e.target.value)}
            placeholder="思ったことをそのまま書いてOK。ここはあなただけのスペースだよ。"
            style={{
              width: "100%",
              height: 80,
              border: "1.5px solid var(--color-orange-100)",
              background: "var(--color-panel)",
              borderRadius: 13,
              padding: 13,
              font: "500 13px/1.6 'M PLUS Rounded 1c'",
              color: "var(--color-text)",
              resize: "none",
            }}
          />
        </div>

        <div style={{ background: "var(--color-panel)", borderRadius: 20, padding: "20px 22px" }}>
          <div style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)", marginBottom: 12 }}>
            これまでの日報
          </div>
          <ReportHistoryTable items={history} onSelect={setSelectedItem} />
        </div>
      </div>

      <Dialog open={selectedItem !== null} onClose={() => setSelectedItem(null)} title={selectedItem?.date}>
        {selectedItem ? <ReportHistoryDetail item={selectedItem} /> : null}
      </Dialog>

      <Dialog open={draftListOpen} onClose={() => setDraftListOpen(false)} title="保存した下書き">
        <ReportDraftList
          items={drafts}
          onSelect={(item) => {
            loadDraft(item);
            setDraftListOpen(false);
          }}
          onDelete={deleteDraft}
        />
      </Dialog>
    </PageContainer>
  );
}
