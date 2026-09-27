import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "./AuthProvider";

/**
 * !NOTE: `loading`中は何も描画しない。ここで`/login`へ先にリダイレクトしてしまうと、
 *        `GET /api/auth/me`の応答を待たずに一瞬ログイン画面が表示されてしまうため。
 *        未ログインが確定した時点で、元のパスを`state.from`に保持して`/login`へ遷移させ、
 *        ログイン成功後に元の画面へ戻れるようにする。
 *
 * !NOTE: ただし利用者自身がログアウトした場合は元のパスを渡さない。次にログインするのが別の
 *        ユーザーの場合、前のユーザーが開いていた画面(その人の課題詳細等)へ着地してしまうため。
 *        セッション切れ(401)の場合は同じ利用者が再ログインする想定なので、元の画面へ戻す。
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { status, loggedOutByUser } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return null;
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" state={loggedOutByUser ? undefined : { from: location }} replace />;
  }

  return <>{children}</>;
}
