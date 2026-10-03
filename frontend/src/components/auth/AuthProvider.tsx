import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { apiClient, setUnauthorizedHandler } from "../../lib/apiClient";
import { clearAutosave } from "../../features/report/reportAutosave";
import { clearWorkspaces } from "../../features/assignment/workspaceStorage";
import type { CurrentUser } from "../../lib/types";

export type UserRole = "member" | "admin";

export const ROLE_LABEL: Record<UserRole, string> = {
  member: "新入社員",
  admin: "講師",
};

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: CurrentUser | null;
  /** 直近の未ログイン状態が、利用者自身のログアウト操作によるものか(セッション切れ・初回表示ではfalse) */
  loggedOutByUser: boolean;
  login: (loginId: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

/**
 * !NOTE: マウント時に`GET /api/auth/me`でログイン状態を確認し、`apiClient`の401ハンドラも
 *        ここで登録する。以後どのAPIが401を返しても(`/api/auth/*`自体は除く)未ログイン状態へ
 *        戻すことで、セッション期限切れ・Cookie削除後の操作を`/login`へ確実に戻す。
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loggedOutByUser, setLoggedOutByUser] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<CurrentUser>("/api/auth/me")
      .then((data) => {
        if (cancelled) return;
        setUser(data);
        setStatus("authenticated");
      })
      .catch(() => {
        if (cancelled) return;
        setUser(null);
        setStatus("unauthenticated");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearWorkspaces();
      setUser(null);
      setStatus("unauthenticated");
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const login = useCallback(async (loginId: string, password: string) => {
    const data = await apiClient.post<CurrentUser>("/api/auth/login", { loginId, password });
    setUser(data);
    setLoggedOutByUser(false);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.post<void>("/api/auth/logout", undefined);
    } finally {
      // !NOTE: ログアウト時は日報の自動保存(localStorage)も消去する。消去しないと、同じ
      //        ブラウザで別のユーザーがログインしたとき、前のユーザーの書きかけの日報が
      //        復元候補として出てしまう(docs/screens/login.md参照)。
      clearAutosave();
      clearWorkspaces();
      setUser(null);
      setLoggedOutByUser(true);
      setStatus("unauthenticated");
    }
  }, []);

  const value = useMemo(
    () => ({ status, user, loggedOutByUser, login, logout }),
    [status, user, loggedOutByUser, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
