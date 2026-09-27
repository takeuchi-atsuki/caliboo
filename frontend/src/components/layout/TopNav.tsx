import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";

import { Mascot } from "../mascot/Mascot";
import { StreakBadge } from "../badge/StreakBadge";
import { PhosphorIcon } from "../icon/PhosphorIcon";
import { useThemeMode } from "../theme/ThemeModeProvider";
import { ROLE_LABEL, useAuth } from "../auth/AuthProvider";

const NAV_ITEMS = [
  { label: "ホーム", to: "/home" },
  { label: "日報", to: "/report" },
  { label: "課題", to: "/assignments" },
  { label: "強み", to: "/strengths" },
  { label: "資格勉強", to: "/study" },
  { label: "OJT", to: "/ojt" },
];

export interface TopNavProps {
  streakDays?: number;
}

/**
 * !NOTE: 画面遷移を伴う実際のページナビゲーションのため、パネル切替を意味する
 *        MUIの`Tabs`(role="tablist")ではなく、通常の`Link`をAppBar/Toolbarで
 *        構造化する構成にしている。`position="static"`にしているのは、
 *        MUIのAppBar既定値(fixed)にすると画面上部に固定されレイアウトが
 *        変わってしまうため、元々の「通常フローに従うヘッダー」という挙動を保つ。
 */
export function TopNav({ streakDays = 12 }: TopNavProps) {
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const { mode, toggleMode } = useThemeMode();
  const { user, logout } = useAuth();

  // !NOTE: RequireAuthが未ログイン中はこのページ自体を描画しないため、通常は必ずuserが
  //        存在する。型を絞り込むためのガードで、実際に到達することは想定していない。
  if (!user) {
    return null;
  }

  const initials = user.displayName.slice(0, 1);

  return (
    <AppBar
      position="static"
      elevation={0}
      sx={{ background: "var(--color-panel)", borderBottom: "1px solid var(--color-border-soft)" }}
    >
      {/* !NOTE: xs幅では余白・間隔を詰め、アバターを隠す。詰めないと幅375〜400pxの画面で右端の
                 ログアウトボタンが画面外に出る。xsでは表示名・ロールも隠れるため、アバターも省く。 */}
      <Toolbar
        disableGutters
        sx={{
          padding: { xs: "0 12px", md: "0 32px" },
          gap: { xs: "8px", md: "30px" },
          height: "62px",
          minHeight: "62px !important",
        }}
      >
        <IconButton
          onClick={() => setNavOpen(true)}
          aria-label="メニューを開く"
          sx={{ display: { xs: "inline-flex", md: "none" } }}
        >
          <PhosphorIcon name="ph ph-list" size={22} color="var(--color-text)" />
        </IconButton>
        <Box
          component={Link}
          to="/home"
          sx={{ display: "flex", alignItems: "center", gap: "9px", marginRight: { xs: 0, md: "8px" }, textDecoration: "none" }}
        >
          <Mascot size={30} color="var(--color-green-300)" mood="cheer" />
          <Box component="span" sx={{ fontWeight: 800, fontSize: 20, color: "var(--color-text)" }}>
            Caliboo
          </Box>
        </Box>
        <Box sx={{ display: { xs: "none", md: "flex" }, gap: "30px" }}>
          {NAV_ITEMS.map((item) => {
            const active = location.pathname.startsWith(item.to);
            return (
              <Box
                key={item.to}
                component={Link}
                to={item.to}
                sx={{
                  fontWeight: active ? 700 : 600,
                  fontSize: 14,
                  color: active ? "var(--color-green-500)" : "var(--color-text-sub)",
                  borderBottom: active ? "3px solid var(--color-green-400)" : "3px solid transparent",
                  height: "62px",
                  display: "flex",
                  alignItems: "center",
                  textDecoration: "none",
                }}
              >
                {item.label}
              </Box>
            );
          })}
        </Box>
        <Box sx={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: { xs: "8px", sm: "14px" } }}>
          <Box
            sx={{
              display: { xs: "none", sm: "flex" },
              flexDirection: "column",
              alignItems: "flex-end",
              lineHeight: 1.3,
            }}
          >
            <Box component="span" sx={{ fontWeight: 700, fontSize: 13, color: "var(--color-text)" }}>
              {user.displayName}
            </Box>
            <Box component="span" sx={{ fontWeight: 600, fontSize: 11, color: "var(--color-text-sub)" }}>
              {ROLE_LABEL[user.role]}
            </Box>
          </Box>
          <IconButton
            onClick={toggleMode}
            aria-label={mode === "dark" ? "ライトモードに切り替える" : "ダークモードに切り替える"}
          >
            <PhosphorIcon
              name={mode === "dark" ? "ph-fill ph-sun" : "ph-fill ph-moon"}
              size={20}
              color="var(--color-text-sub2)"
            />
          </IconButton>
          <StreakBadge days={streakDays} />
          <Avatar
            sx={{
              display: { xs: "none", sm: "flex" },
              width: 36,
              height: 36,
              background: "var(--color-purple-200)",
              fontWeight: 800,
              fontSize: 13,
              color: "var(--color-purple-500)",
            }}
          >
            {initials}
          </Avatar>
          <IconButton onClick={() => void logout()} aria-label="ログアウト">
            <PhosphorIcon name="ph-bold ph-sign-out" size={20} color="var(--color-text-sub2)" />
          </IconButton>
        </Box>
      </Toolbar>
      <Drawer anchor="left" open={navOpen} onClose={() => setNavOpen(false)}>
        <List sx={{ width: 220, padding: "10px 0" }}>
          {NAV_ITEMS.map((item) => {
            const active = location.pathname.startsWith(item.to);
            return (
              <ListItemButton
                key={item.to}
                component={Link}
                to={item.to}
                onClick={() => setNavOpen(false)}
                sx={{
                  padding: "12px 22px",
                  fontWeight: active ? 700 : 600,
                  color: active ? "var(--color-green-500)" : "var(--color-text)",
                }}
              >
                {item.label}
              </ListItemButton>
            );
          })}
        </List>
      </Drawer>
    </AppBar>
  );
}
