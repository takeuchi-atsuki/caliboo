import { useEffect, useRef } from "react";
import Box from "@mui/material/Box";

import type { ChatMessage } from "../../lib/types";
import { ChatBubble } from "./ChatBubble";

export interface ChatMessageListProps {
  messages: ChatMessage[];
  botIconBg?: string;
  botIconColor?: string;
  meBg?: string;
}

export function ChatMessageList({ messages, botIconBg, botIconColor, meBg }: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length]);

  return (
    <Box sx={{ flex: 1, overflowY: "auto", padding: "22px 26px", display: "flex", flexDirection: "column", gap: "15px" }}>
      {messages.map((message) => (
        <ChatBubble
          key={message.id}
          message={message}
          botIconBg={botIconBg}
          botIconColor={botIconColor}
          meBg={meBg}
        />
      ))}
      <div ref={bottomRef} />
    </Box>
  );
}
