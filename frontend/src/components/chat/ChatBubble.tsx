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
          maxWidth: { xs: "88%", sm: "74%" },
          background: meBg,
          borderRadius: "17px 4px 17px 17px",
          padding: "12px 16px",
          font: "400 15px/1.8 var(--font-body)",
          color: "var(--color-on-pastel)",
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere",
        }}
      >
        {message.text}
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", gap: "11px", alignItems: "flex-start", maxWidth: { xs: "96%", sm: "78%" } }}>
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
      <Box sx={{ minWidth: 0 }}>
        <Box
          sx={{
            background: "var(--color-panel)",
            borderRadius: "4px 17px 17px 17px",
            padding: "13px 16px",
            font: "400 15px/1.8 var(--font-body)",
            color: "var(--color-text)",
            border: "1px solid var(--color-border-soft)",
            whiteSpace: "pre-wrap",
            overflowWrap: "anywhere",
          }}
        >
          {message.text}
        </Box>
        {message.references.length > 0 ? (
          <Box sx={{ display: "flex", gap: "8px", marginTop: "6px", flexWrap: "wrap" }}>
            {message.references.map((ref, index) => (
              <Box
                component="div"
                key={`${ref.knowledgeId ?? ref.label}-${index}`}
                sx={{
                  background: "var(--color-green-100)",
                  borderRadius: "11px",
                  padding: "7px 12px",
                  fontWeight: 600,
                  fontSize: 11.5,
                  color: "var(--color-green-500)",
                  maxWidth: "100%", overflowWrap: "anywhere",
                }}
              >
                {ref.label}
                {ref.quote && <Box component="blockquote" sx={{ m: 0, mt: 0.5, fontWeight: 400, whiteSpace: "pre-wrap" }}>{ref.quote}</Box>}
              </Box>
            ))}
          </Box>
        ) : null}
      </Box>
    </Box>
  );
}
