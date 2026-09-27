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
  padding: "13px 16px",
  font: "400 16px/1.6 var(--font-body)",
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
          : err instanceof ApiError && err.status === 429
            ? "ログイン試行が多すぎます。最大15分待ってから再度お試しください。"
            : "ログインできませんでした。時間をおいて再度お試しください。",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100dvh",
        background: "radial-gradient(ellipse at 20% 15%, var(--color-pink-100), transparent 55%), radial-gradient(ellipse at 80% 85%, var(--color-green-100), transparent 55%), var(--color-bg)",
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
          width: 420,
          maxWidth: "100%",
          background: "var(--color-panel)",
          borderRadius: "var(--radius-lg)",
          padding: { xs: "32px 24px", sm: "40px" },
          border: "1px solid var(--color-border-soft)",
          boxShadow: "var(--shadow-float)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "18px",
        }}
      >
        <Mascot size={72} color="var(--color-green-300)" mood="cheer" />
        <Box sx={{ textAlign: "center" }}>
          <Box component="h1" sx={{ m: 0, fontFamily: "'Nunito', sans-serif", fontWeight: 800, fontSize: 32, letterSpacing: "-0.04em", color: "var(--color-text)" }}>Caliboo</Box>
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
