import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";

import { Mascot } from "../../components/mascot/Mascot";
import { Button } from "../../components/ui/Button";
import { useAuth } from "../../components/auth/AuthProvider";
import { ApiError } from "../../lib/apiClient";

interface LoginLocationState {
  from?: { pathname: string; search?: string; hash?: string };
}

const inputStyle = {
  width: "100%",
  boxSizing: "border-box" as const,
  border: "1.5px solid var(--color-border)",
  background: "var(--color-bg)",
  borderRadius: 13,
  padding: "11px 14px",
  font: "500 13.5px/1.6 'M PLUS Rounded 1c'",
  color: "var(--color-text)",
};

const labelStyle = {
  fontWeight: 700,
  fontSize: 12.5,
  color: "var(--color-text-sub)",
};

/**
 * !NOTE: ログイン成功はAuthProviderの`status`を`authenticated`へ変えることで表現し、
 *        遷移はこのコンポーネントのレンダー時チェック(`status === "authenticated"`なら
 *        `<Navigate>`)に一本化している。`handleSubmit`側で個別に`navigate()`を呼ぶ実装
 *        にすると、既にログイン済みで`/login`を開いた場合の遷移ロジックと二重化し、
 *        遷移先が競合する余地が生まれるため。
 */
export function LoginPage() {
  const { status, login } = useAuth();
  const location = useLocation();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const from = (location.state as LoginLocationState | null)?.from;
  const fromPath = from ? `${from.pathname}${from.search ?? ""}${from.hash ?? ""}` : "/home";

  if (status === "authenticated") {
    return <Navigate to={fromPath} replace />;
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    try {
      await login(loginId, password);
    } catch (err) {
      setErrorMessage(
        err instanceof ApiError && err.status === 401
          ? "ログインIDまたはパスワードが正しくありません"
          : "ログインできませんでした。時間をおいて再度お試しください。",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <Box
        component="form"
        onSubmit={handleSubmit}
        sx={{
          width: 360,
          maxWidth: "100%",
          background: "var(--color-panel)",
          borderRadius: "26px",
          padding: "34px 30px",
          boxShadow: "0 6px 20px var(--color-border-soft)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "18px",
        }}
      >
        <Mascot size={72} color="var(--color-green-300)" mood="cheer" />
        <Box sx={{ textAlign: "center" }}>
          <Box sx={{ fontWeight: 800, fontSize: 22, color: "var(--color-text)" }}>Caliboo</Box>
          <Box sx={{ fontWeight: 500, fontSize: 12.5, color: "var(--color-text-sub)", marginTop: "4px" }}>
            ログインして始めよう
          </Box>
        </Box>

        {errorMessage ? (
          <Alert severity="error" sx={{ width: "100%" }}>
            {errorMessage}
          </Alert>
        ) : null}

        <Box sx={{ width: "100%", display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="login-id" style={labelStyle}>
            ログインID
          </label>
          <input
            id="login-id"
            value={loginId}
            onChange={(e) => setLoginId(e.target.value)}
            autoComplete="username"
            style={inputStyle}
          />
        </Box>

        <Box sx={{ width: "100%", display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="login-password" style={labelStyle}>
            パスワード
          </label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            style={inputStyle}
          />
        </Box>

        <Button
          type="submit"
          icon="ph-bold ph-sign-in"
          disabled={submitting || loginId.trim() === "" || password === ""}
          style={{ width: "100%", justifyContent: "center" }}
        >
          ログイン
        </Button>
      </Box>
    </Box>
  );
}
