import { Alert, Button as MuiButton } from "@mui/material";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";

import { PageContainer } from "../../components/layout/PageContainer";
import { Mascot } from "../../components/mascot/Mascot";
import { DeptCard } from "../../components/dept/DeptCard";
import { ChatMessageList } from "../../components/chat/ChatMessageList";
import { ChatComposer } from "../../components/chat/ChatComposer";
import { QuickQuestionChips } from "../../components/chat/QuickQuestionChips";
import { PhosphorIcon } from "../../components/icon/PhosphorIcon";
import { useOjt } from "./useOjt";

export function OjtChatPage() {
  const {
    departments,
    selectedDept,
    messages,
    input,
    setInput,
    selectDept,
    backToDeptList,
    sendMessage, error, sending, escalated, escalate,
    quickAsks,
  } = useOjt();

  if (!selectedDept) {
    return (
      <PageContainer>
        {error && <Alert severity="error">{error}</Alert>}
        <div style={{ padding: "var(--page-gutter)", minHeight: 560 }}>
          <div style={{ display: "flex", gap: 14, marginBottom: 6 }}>
            <Mascot size={48} color="var(--color-green-200)" mood="cheer" />
            <div>
              <h1 style={{ margin: 0, fontWeight: 800, fontSize: 24, color: "var(--color-text)" }}>
                どの課のことを聞きたい？
              </h1>
              <div style={{ fontWeight: 500, fontSize: 13, color: "var(--color-text-sub)" }}>
                課を選ぶとAIメンターに相談できます
              </div>
            </div>
          </div>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "repeat(3,1fr)" },
              gap: "18px",
              marginTop: "24px",
            }}
          >
            {departments.map((dept) => (
              <DeptCard key={dept.id} dept={dept} onSelect={selectDept} layout="grid" />
            ))}
          </Box>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div style={{ display: "flex", flexDirection: "column", height: 620 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "16px 24px",
            background: "var(--color-panel)",
            borderBottom: "1px solid var(--color-border-soft)",
          }}
        >
          <IconButton
            onClick={backToDeptList}
            aria-label="課選択に戻る"
            sx={{
              width: 38,
              height: 38,
              borderRadius: "12px",
              background: "var(--color-bg)",
              "&:hover": { background: "var(--color-bg)" },
            }}
          >
            <PhosphorIcon name="ph ph-caret-left" size={18} color="var(--color-text)" />
          </IconButton>
          <Mascot size={40} color="var(--color-green-200)" mood="happy" />
          <div style={{ flex: 1, minWidth: 0, overflowWrap: "anywhere" }}>
            <div style={{ fontWeight: 800, fontSize: 16, color: "var(--color-text)" }}>
              {selectedDept.name} メンター
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 5, fontWeight: 600, fontSize: 11, color: "var(--color-green-500)" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--color-green-400)" }} />
              テンプレートによる自動回答
            </div>
          </div>
        </div>
        <ChatMessageList messages={messages} botIconBg="var(--color-green-200)" botIconColor="var(--color-green-500)" meBg="var(--color-green-400)" />
        <div style={{ padding: "16px 24px", background: "var(--color-panel)", borderTop: "1px solid var(--color-border-soft)" }}>
          <QuickQuestionChips questions={quickAsks} onSelect={sendMessage} hoverColor="var(--color-green-500)" />
          {error && <Alert severity="error">{error}</Alert>}
          <MuiButton disabled={sending || escalated} onClick={() => void escalate()}>{escalated ? "講師に相談済み" : "講師に相談"}</MuiButton>
          <ChatComposer
            value={input}
            onChange={setInput}
            onSend={() => sendMessage(input)}
            placeholder="メンターに質問してみよう…"
            accentColor="var(--color-green-400)"
          />
        </div>
      </div>
    </PageContainer>
  );
}
