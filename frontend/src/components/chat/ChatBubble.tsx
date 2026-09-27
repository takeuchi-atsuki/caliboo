import Box from "@mui/material/Box";

import type { ChatMessage } from "../../lib/types";
import { PhosphorIcon } from "../icon/PhosphorIcon";

export interface ChatBubbleProps {
  message: ChatMessage;
  botIconBg?: string;
  botIconColor?: string;
  meBg?: string;
}

export function ChatBubble({
  message,
  botIconBg = "var(--color-blue-200)",
  botIconColor = "var(--color-blue-500)",
  meBg = "var(--color-blue-400)",
}: ChatBubbleProps) {
  if (message.role === "me") {
    return (
      <Box
        sx={{
          alignSelf: "flex-end",
          maxWidth: "74%",
          background: meBg,
          borderRadius: "17px 4px 17px 17px",
          padding: "12px 16px",
          font: "500 13.5px/1.6 'M PLUS Rounded 1c'",
          color: "var(--color-panel)",
          whiteSpace: "pre-wrap",
        }}
      >
        {message.text}
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", gap: "11px", alignItems: "flex-start", maxWidth: "78%" }}>
      <Box
        sx={{
          width: 33,
          height: 33,
          flex: "none",
          borderRadius: "50%",
          background: botIconBg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <PhosphorIcon name="ph-fill ph-sparkle" color={botIconColor} size={15} />
      </Box>
      <Box>
        <Box
          sx={{
            background: "var(--color-panel)",
            borderRadius: "4px 17px 17px 17px",
            padding: "13px 16px",
            font: "500 13.5px/1.7 'M PLUS Rounded 1c'",
            color: "var(--color-text)",
            boxShadow: "0 3px 12px var(--color-border-soft)",
            whiteSpace: "pre-wrap",
          }}
        >
          {message.text}
        </Box>
        {message.references.length > 0 ? (
          <Box sx={{ display: "flex", gap: "8px", marginTop: "6px", flexWrap: "wrap" }}>
            {message.references.map((ref) => (
              <Box
                component="span"
                key={ref.label}
                sx={{
                  background: "var(--color-green-100)",
                  borderRadius: "11px",
                  padding: "7px 12px",
                  fontWeight: 600,
                  fontSize: 11.5,
                  color: "var(--color-green-500)",
                }}
              >
                {ref.label}
              </Box>
            ))}
          </Box>
        ) : null}
      </Box>
    </Box>
  );
}
