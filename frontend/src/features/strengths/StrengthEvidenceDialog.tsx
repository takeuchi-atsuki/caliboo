import Box from "@mui/material/Box";

import { Dialog } from "../../components/ui/Dialog";
import { Tag } from "../../components/badge/Tag";
import {
  confidencePercent,
  evidenceSourceLabel,
  strengthStatusLabel,
  strengthStatusTone,
} from "../../lib/strengthStatus";
import type { StrengthItem } from "../../lib/types";

export interface StrengthEvidenceDialogProps {
  strength: StrengthItem | null;
  onClose: () => void;
}

export function StrengthEvidenceDialog({ strength, onClose }: StrengthEvidenceDialogProps) {
  return (
    <Dialog
      open={strength !== null}
      onClose={onClose}
      title={strength ? `${strength.layerTask.skillName} の根拠` : ""}
    >
      {strength ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Tag
              label={strengthStatusLabel(strength.status)}
              tone={strengthStatusTone(strength.status)}
            />
            <Box component="span" sx={{ fontWeight: 600, fontSize: 12, color: "var(--color-text-sub)" }}>
              確信度 {confidencePercent(strength.confidence)}％ ／ 根拠 {strength.evidence.length}件
            </Box>
          </Box>

          {strength.evidence.map((evidence) => (
            <Box
              key={`${evidence.source.kind}-${evidence.source.field}-${evidence.source.iteration ?? ""}`}
              sx={{
                padding: "12px 14px",
                borderRadius: "14px",
                background: "var(--color-bg)",
                border: "1px solid var(--color-border-soft)",
              }}
            >
              <Box sx={{ fontWeight: 700, fontSize: 11.5, color: "var(--color-text-sub2)" }}>
                {evidenceSourceLabel(evidence.source)}
              </Box>
              <Box sx={{ fontWeight: 500, fontSize: 13, color: "var(--color-text)", marginTop: "5px" }}>
                「{evidence.quote}」
              </Box>
            </Box>
          ))}

          <Box sx={{ fontWeight: 500, fontSize: 12, color: "var(--color-text-sub)" }}>
            {strength.learningAgility.note}
          </Box>
        </Box>
      ) : null}
    </Dialog>
  );
}
