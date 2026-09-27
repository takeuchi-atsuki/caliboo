import { useId, useRef } from "react";
import MuiDialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogActions from "@mui/material/DialogActions";
import Button, { type ButtonProps as MuiButtonProps } from "@mui/material/Button";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmColor?: MuiButtonProps["color"];
  // 送信中の二重実行(連打)を防ぐために確認ボタンを無効化したい場合に指定する。既定は無効化しない。
  confirmDisabled?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * !NOTE: 削除等の破壊的操作だけでなく、配信・見送りなど「元に戻せない/後戻りしにくい」
 *        操作全般の確認に使う共通ダイアログ。誤操作防止のため初期フォーカスは常に
 *        「キャンセル」側に置く。確認ボタンの色は`confirmColor`で操作の性質(危険/肯定)に
 *        合わせて指定でき、既定は破壊的操作向けの`error`。
 */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "削除する",
  cancelLabel = "キャンセル",
  confirmColor = "error",
  confirmDisabled = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  return (
    <MuiDialog
      open={open}
      onClose={onCancel}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      // !NOTE: このダイアログは他のDialog(下書き一覧)の中から開かれるネスト構成になる。
      //        MUIのFocusTrapは初期フォーカスをDialog自身(Paper)に当ててしまい、
      //        Buttonの`autoFocus`と競合して上書きされるため、Transitionの
      //        `onEntered`で明示的に「キャンセル」ボタンへフォーカスし直している。
      slotProps={{
        transition: {
          onEntered: () => cancelButtonRef.current?.focus(),
        },
      }}
    >
      <DialogTitle id={titleId} sx={{ fontWeight: 800, fontSize: 17, color: "var(--color-text)" }}>
        {title}
      </DialogTitle>
      <DialogContent>
        <DialogContentText id={descriptionId} sx={{ fontSize: 13.5, color: "var(--color-text)" }}>
          {message}
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ padding: "8px 16px 16px" }}>
        <Button ref={cancelButtonRef} onClick={onCancel} sx={{ textTransform: "none" }}>
          {cancelLabel}
        </Button>
        <Button onClick={onConfirm} color={confirmColor} disabled={confirmDisabled} sx={{ textTransform: "none" }}>
          {confirmLabel}
        </Button>
      </DialogActions>
    </MuiDialog>
  );
}
