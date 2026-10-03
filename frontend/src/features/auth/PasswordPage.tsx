import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { Alert, Button, Stack, TextField, Typography } from "@mui/material";

import { useAuth } from "../../components/auth/AuthProvider";
import { PageContainer } from "../../components/layout/PageContainer";
import { apiClient, ApiError } from "../../lib/apiClient";

export function PasswordPage({ mode }: { mode: "change" | "reset" }) {
  const { logout } = useAuth();
  const [loginId, setLoginId] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [resetCode, setResetCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const isReset = mode === "reset";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      setMessage("新しいパスワードが一致しません。");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await apiClient.post<void>(isReset ? "/api/auth/reset-password" : "/api/auth/change-password",
        isReset ? { loginId, resetCode, newPassword } : { currentPassword, newPassword });
      setDone(true);
      setCurrentPassword("");
      setResetCode("");
      setNewPassword("");
      setConfirmPassword("");
      if (!isReset) await logout();
    } catch (error) {
      setMessage(error instanceof ApiError && error.status === 429
        ? "試行回数が多すぎます。最大15分待ってからお試しください。"
        : error instanceof ApiError && error.status === 401
          ? isReset ? "ログインIDまたは再設定コードが正しくないか、有効期限が切れています。" : "現在のパスワードが正しくありません。"
          : "変更できませんでした。入力を確認して再度お試しください。");
    } finally {
      setBusy(false);
    }
  }

  return <PageContainer><Stack component="form" onSubmit={(event) => void submit(event)} spacing={2} sx={{ maxWidth: 440, mx: "auto", p: 3 }}>
    <Typography component="h1" variant="h5">{isReset ? "パスワードを再設定" : "パスワードを変更"}</Typography>
    {isReset && <Typography variant="body2">管理者に本人確認を依頼し、発行された再設定コードを入力してください。コードは15分間有効です。</Typography>}
    {message && <Alert severity="error">{message}</Alert>}
    {done && <Alert severity="success">パスワードを更新しました。新しいパスワードでログインしてください。</Alert>}
    {isReset ? <>
      <TextField required label="ログインID" autoComplete="username" value={loginId} onChange={(event) => setLoginId(event.target.value)} />
      <TextField required label="再設定コード" autoComplete="off" value={resetCode} onChange={(event) => setResetCode(event.target.value)} />
    </> : <TextField required label="現在のパスワード" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />}
    <TextField required label="新しいパスワード" type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} slotProps={{ htmlInput: { minLength: 12, maxLength: 128 } }} helperText="12〜128文字" />
    <TextField required label="新しいパスワード（確認）" type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
    <Button type="submit" variant="contained" disabled={busy}>更新する</Button>
    {isReset && <Button component={Link} to="/login">ログインへ戻る</Button>}
  </Stack></PageContainer>;
}
