import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import IconButton from "@mui/material/IconButton";
import { Alert, Button, Typography } from "@mui/material";

import { PageContainer } from "../../components/layout/PageContainer";
import { CollapsibleAside } from "../../components/layout/CollapsibleAside";
import { Mascot } from "../../components/mascot/Mascot";
import { ChatMessageList } from "../../components/chat/ChatMessageList";
import { ChatComposer } from "../../components/chat/ChatComposer";
import { QuickQuestionChips } from "../../components/chat/QuickQuestionChips";
import { PhosphorIcon } from "../../components/icon/PhosphorIcon";
import { useStudyChat } from "./useStudyChat";
import { readQuizHandoff } from "./quizHandoff";

export function StudyChatPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const handoff = readQuizHandoff(location.state);
  const { relatedQuestions, relatedError, messages, input, setInput, sendMessage, quickQuestions,
    sending, error, canRetry, retry } = useStudyChat(handoff);

  // !NOTE: location.stateはリロード後も履歴に残るため、受け取った時点で消す。
  //        消さないとリロードのたびに同じ問題の質問が再表示される。
  const hasHandoff = handoff !== null;
  useEffect(() => {
    if (hasHandoff) navigate(location.pathname, { replace: true, state: null });
  }, [hasHandoff, location.pathname, navigate]);

  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <PageContainer>
      <div style={{ display: "flex", height: 640 }}>
        <CollapsibleAside
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          width={264}
          title="関連する過去問"
          sx={{
            background: "var(--color-panel)",
            borderRight: "1px solid var(--color-border-soft)",
            padding: "22px 16px",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 7, fontWeight: 800, fontSize: 14, color: "var(--color-text)" }}>
            <i className="ph-fill ph-cards" style={{ color: "var(--color-blue-500)", fontSize: 17 }} />
            関連する過去問
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
            {relatedError && <Alert severity="warning">{relatedError}</Alert>}
            {relatedQuestions.map((item) => (
              <div
                key={item.id}
                style={{ border: "1px solid var(--color-border)", borderRadius: 14, padding: 13, cursor: "pointer" }}
              >
                <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--color-text)" }}>{item.title}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 10.5, color: "var(--color-text-sub)" }}>{item.questionCount}問</span>
                  {item.tags.map((tag) => (
                    <span
                      key={tag}
                      style={{
                        fontWeight: 700,
                        fontSize: 10,
                        color: tag === "苦手" ? "var(--color-pink-500)" : "var(--color-blue-500)",
                        background: tag === "苦手" ? "var(--color-pink-100)" : "var(--color-blue-100)",
                        padding: "2px 8px",
                        borderRadius: 8,
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div
            style={{
              marginTop: "auto",
              background: "var(--color-blue-100)",
              borderRadius: 15,
              padding: 14,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <Mascot size={36} color="var(--color-blue-200)" mood="cheer" />
            <div style={{ fontWeight: 600, fontSize: 11.5, lineHeight: 1.45, color: "var(--color-blue-500)" }}>
              わからない所は
              <br />
              気軽に聞いてね！
            </div>
          </div>
        </CollapsibleAside>
        <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", background: "var(--color-bg)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "15px 24px", background: "var(--color-panel)", borderBottom: "1px solid var(--color-border-soft)" }}>
            <IconButton
              onClick={() => setSidebarOpen(true)}
              aria-label="関連する過去問を開く"
              sx={{ display: { xs: "inline-flex", md: "none" } }}
            >
              <PhosphorIcon name="ph ph-list" size={20} color="var(--color-text)" />
            </IconButton>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: "50%",
                background: "var(--color-blue-200)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <i className="ph-fill ph-sparkle" style={{ color: "var(--color-blue-500)", fontSize: 18 }} />
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 16, color: "var(--color-text)" }}>学習サポートAI</div>
              <div style={{ display: "flex", alignItems: "center", gap: 5, fontWeight: 600, fontSize: 11, color: "var(--color-blue-500)" }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--color-blue-400)" }} />
                基本情報技術者モード
              </div>
            </div>
          </div>
          {error && <Alert severity="error" action={canRetry && <Button disabled={sending} onClick={() => void retry()}>再送する</Button>}>{error}</Alert>}
          {sending && <Typography role="status" sx={{ px: 3, py: 1 }}>回答を考えています…</Typography>}
          <ChatMessageList messages={messages} botIconBg="var(--color-blue-200)" botIconColor="var(--color-blue-500)" meBg="var(--color-blue-400)" />
          <div style={{ padding: "16px 24px", background: "var(--color-panel)", borderTop: "1px solid var(--color-border-soft)" }}>
            <QuickQuestionChips questions={quickQuestions} onSelect={sendMessage} hoverColor="var(--color-blue-500)" />
            <ChatComposer
              value={input}
              onChange={setInput}
              onSend={() => sendMessage(input)}
              placeholder="問題の解き方や用語を質問してみよう…"
              accentColor="var(--color-blue-400)"
            />
          </div>
        </main>
      </div>
    </PageContainer>
  );
}
