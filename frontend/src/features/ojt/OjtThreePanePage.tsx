import { Alert, Button as MuiButton } from "@mui/material";
import { useEffect, useState } from "react";
import IconButton from "@mui/material/IconButton";

import { PageContainer } from "../../components/layout/PageContainer";
import { CollapsibleAside } from "../../components/layout/CollapsibleAside";
import { Mascot } from "../../components/mascot/Mascot";
import { DeptCard } from "../../components/dept/DeptCard";
import { KnowledgeCard } from "../../components/dept/KnowledgeCard";
import { ChatMessageList } from "../../components/chat/ChatMessageList";
import { ChatComposer } from "../../components/chat/ChatComposer";
import { PhosphorIcon } from "../../components/icon/PhosphorIcon";
import { useOjt } from "./useOjt";

export function OjtThreePanePage() {
  const { departments, selectedDept, messages, knowledge, input, setInput, selectDept, sendMessage, error, sending, escalated, escalate } =
    useOjt();
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);

  useEffect(() => {
    if (!selectedDept && departments.length > 0) {
      selectDept(departments[0].id);
    }
  }, [departments, selectedDept, selectDept]);

  return (
    <PageContainer>
      <div style={{ display: "flex", height: 600 }}>
        <CollapsibleAside
          open={leftOpen}
          onClose={() => setLeftOpen(false)}
          width={230}
          title="課をえらぶ"
          sx={{
            background: "var(--color-panel)",
            borderRight: "1px solid var(--color-border-soft)",
            padding: "20px 14px",
            display: "flex",
            flexDirection: "column",
            gap: "5px",
          }}
        >
          <div style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)", padding: "0 8px 8px" }}>
            課をえらぶ
          </div>
          {departments.map((dept) => (
            <DeptCard
              key={dept.id}
              dept={dept}
              selected={dept.id === selectedDept?.id}
              onSelect={(id) => {
                selectDept(id);
                setLeftOpen(false);
              }}
              layout="list"
            />
          ))}
        </CollapsibleAside>
        <main style={{ flex: 618, minWidth: 0, display: "flex", flexDirection: "column", background: "var(--color-bg)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "15px 22px", background: "var(--color-panel)" }}>
            <IconButton
              onClick={() => setLeftOpen(true)}
              aria-label="課一覧を開く"
              sx={{ display: { xs: "inline-flex", md: "none" } }}
            >
              <PhosphorIcon name="ph ph-list" size={20} color="var(--color-text)" />
            </IconButton>
            <Mascot size={38} color="var(--color-blue-200)" mood="happy" />
            <div>
              <div style={{ fontWeight: 800, fontSize: 16, color: "var(--color-text)" }}>
                {selectedDept ? `${selectedDept.name} メンター` : "課を選んでください"}
              </div>
              {selectedDept ? (
                <div style={{ fontWeight: 600, fontSize: 11, color: "var(--color-blue-500)" }}>
                  {selectedDept.knowledgeCount}件のナレッジを学習済み
                </div>
              ) : null}
            </div>
            <IconButton
              onClick={() => setRightOpen(true)}
              aria-label="参照ナレッジを開く"
              sx={{ display: { xs: "inline-flex", md: "none" }, marginLeft: "auto" }}
            >
              <PhosphorIcon name="ph ph-books" size={20} color="var(--color-text)" />
            </IconButton>
          </div>
          <ChatMessageList messages={messages} botIconBg="var(--color-blue-200)" botIconColor="var(--color-blue-500)" meBg="var(--color-blue-400)" />
          <div style={{ padding: "15px 22px", background: "var(--color-panel)", borderTop: "1px solid var(--color-border-soft)" }}>
            {error && <Alert severity="error">{error}</Alert>}
          <MuiButton disabled={sending || escalated} onClick={() => void escalate()}>{escalated ? "講師に相談済み" : "講師に相談"}</MuiButton>
          <ChatComposer
              value={input}
              onChange={setInput}
              onSend={() => sendMessage(input)}
              placeholder="メンターに質問してみよう…"
              accentColor="var(--color-blue-400)"
            />
          </div>
        </main>
        <CollapsibleAside
          open={rightOpen}
          onClose={() => setRightOpen(false)}
          anchor="right"
          width={382}
          title="参照ナレッジ"
          sx={{
            background: "var(--color-panel)",
            borderLeft: "1px solid var(--color-border-soft)",
            padding: "20px 18px",
            overflowY: "auto",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 800, fontSize: 13, color: "var(--color-text)", marginBottom: 14 }}>
            <i className="ph ph-books" style={{ color: "var(--color-blue-500)" }} />
            参照ナレッジ
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
            {knowledge.map((item) => (
              <KnowledgeCard key={item.id} item={item} />
            ))}
          </div>
        </CollapsibleAside>
      </div>
    </PageContainer>
  );
}
