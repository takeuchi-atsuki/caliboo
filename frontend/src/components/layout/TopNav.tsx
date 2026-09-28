import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { AppBar, Avatar, Box, ButtonBase, Drawer, IconButton, List, ListItemButton, Toolbar, Typography, useMediaQuery } from "@mui/material";
import { useTheme } from "@mui/material/styles";

import { Mascot } from "../mascot/Mascot";
import { StreakBadge } from "../badge/StreakBadge";
import { PhosphorIcon } from "../icon/PhosphorIcon";
import { useThemeMode } from "../theme/ThemeModeProvider";
import { ROLE_LABEL, useAuth } from "../auth/AuthProvider";

const NAV_ITEMS = [
  { label: "ホーム", to: "/home", icon: "ph ph-house" },
  { label: "日報", to: "/report", icon: "ph ph-note-pencil" },
  { label: "課題", to: "/assignments", icon: "ph ph-check-square" },
  { label: "強み", to: "/strengths", icon: "ph ph-sparkle" },
  { label: "資格勉強", to: "/study", icon: "ph ph-book-open" },
  { label: "OJT", to: "/ojt", icon: "ph ph-chats-circle" },
];
const MOBILE_ITEMS = NAV_ITEMS.filter((item) => ["/home", "/report", "/assignments", "/study"].includes(item.to));
const ADMIN_ITEMS = [
  { label: "ユーザー", to: "/admin/users", icon: "ph ph-users" },
  { label: "相談", to: "/admin/ojt", icon: "ph ph-chat-circle-dots" },
  { label: "OJT設定", to: "/admin/ojt-settings", icon: "ph ph-gear" },
  { label: "解析管理", to: "/admin/agents", icon: "ph ph-chart-line-up" },
];

export interface TopNavProps {
  streakDays?: number;
}

/**
 * !NOTE: ページ遷移はTabsではなくLinkで表現する。下部の「その他」と上部の
 * メニューは同じDrawerを開き、リンクやロール判定が別々にならないようにする。
 */
export function TopNav({ streakDays }: TopNavProps) {
  const { pathname } = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const { mode, toggleMode } = useThemeMode();
  const { user, logout } = useAuth();
  const theme = useTheme();
  const wide = useMediaQuery(theme.breakpoints.up("lg"));
  const active = (to: string) => pathname === to || pathname.startsWith(`${to}/`);

  useEffect(() => {
    if (wide) setNavOpen(false);
  }, [wide]);

  if (!user) return null;

  const navItems = user.role === "admin" ? [...NAV_ITEMS, ...ADMIN_ITEMS] : NAV_ITEMS;
  const moreActive = !MOBILE_ITEMS.some((item) => active(item.to));

  return (
    <>
      <AppBar position="sticky" elevation={0} sx={{ color: "var(--color-text)", background: "var(--color-nav)", backdropFilter: "blur(20px)", borderBottom: "1px solid var(--color-border-soft)" }}>
        <Toolbar disableGutters sx={{ width: "100%", maxWidth: 1440, mx: "auto", px: { xs: 1, sm: 3, lg: 5 }, gap: { xs: 0.5, sm: 1.5 }, minHeight: "68px !important" }}>
          <IconButton
            onClick={() => setNavOpen(true)}
            aria-label="メニューを開く"
            aria-expanded={navOpen}
            aria-controls={navOpen ? "app-navigation" : undefined}
            sx={{ display: { xs: "inline-flex", lg: "none" }, color: "var(--color-text)" }}
          >
            <PhosphorIcon name="ph ph-list" size={23} />
          </IconButton>
          <Box component={Link} to="/home" aria-label="Caliboo ホーム" sx={{ display: "flex", alignItems: "center", gap: 1, textDecoration: "none", flexShrink: 0 }}>
            <Mascot size={32} color="var(--color-green-300)" mood="cheer" />
            <Typography sx={{ display: { xs: "none", sm: "block" }, fontFamily: "'Nunito', sans-serif", fontWeight: 800, fontSize: 24, letterSpacing: "-0.04em", color: "var(--color-text)" }}>Caliboo</Typography>
          </Box>
          <Typography sx={{ display: { xs: "none", md: "block" }, ml: 2, color: "text.secondary", fontSize: 12 }}>小さな一歩を、毎日の成長に。</Typography>
          <Box sx={{ ml: "auto", display: "flex", alignItems: "center", gap: { xs: 0.25, sm: 1 } }}>
            <StreakBadge days={streakDays ?? user.streakDays ?? 0} />
            <IconButton onClick={toggleMode} aria-label={mode === "dark" ? "ライトモードに切り替える" : "ダークモードに切り替える"} sx={{ color: "var(--color-text-sub2)" }}>
              <PhosphorIcon name={mode === "dark" ? "ph ph-sun" : "ph ph-moon"} size={21} />
            </IconButton>
            <Box sx={{ display: { xs: "none", sm: "flex" }, alignItems: "center", gap: 1, ml: 0.5 }}>
              <Avatar sx={{ width: 34, height: 34, bgcolor: "var(--color-purple-100)", color: "var(--color-purple-500)", fontSize: 14, fontWeight: 700 }}>{user.displayName.slice(0, 1)}</Avatar>
              <Box sx={{ maxWidth: 140 }}>
                <Typography noWrap sx={{ fontWeight: 700, fontSize: 12 }}>{user.displayName}</Typography>
                <Typography sx={{ color: "text.secondary", fontSize: 11 }}>{ROLE_LABEL[user.role]}</Typography>
              </Box>
            </Box>
            <IconButton onClick={() => void logout()} aria-label="ログアウト" sx={{ color: "var(--color-text-sub2)" }}>
              <PhosphorIcon name="ph ph-sign-out" size={21} />
            </IconButton>
          </Box>
        </Toolbar>
        <Box component="nav" aria-label="メインナビゲーション" sx={{ display: { xs: "none", lg: "flex" }, width: "100%", maxWidth: 1440, mx: "auto", px: 5, pb: 1.25, gap: 0.75 }}>
          {navItems.map((item) => (
            <ButtonBase component={Link} to={item.to} key={item.to} aria-current={active(item.to) ? "page" : undefined}
              sx={{ minHeight: 44, px: 2, gap: 1, borderRadius: "14px", fontWeight: 700, fontSize: 13, textDecoration: "none", color: active(item.to) ? "var(--color-green-500)" : "var(--color-text-sub2)", bgcolor: active(item.to) ? "var(--color-green-100)" : "transparent", "&:hover": { bgcolor: "var(--color-bg-alt)" } }}>
              <PhosphorIcon name={item.icon} size={19} />{item.label}
            </ButtonBase>
          ))}
        </Box>
      </AppBar>

      <Box component="nav" aria-label="モバイルナビゲーション" sx={{ display: { xs: "grid", sm: "none" }, gridTemplateColumns: "repeat(5, minmax(0, 1fr))", position: "fixed", bottom: 0, left: 0, right: 0, zIndex: theme.zIndex.appBar, bgcolor: "var(--color-nav)", backdropFilter: "blur(20px)", borderTop: "1px solid var(--color-border)", px: 1, pt: 0.5, pb: "calc(4px + env(safe-area-inset-bottom, 0px))" }}>
        {MOBILE_ITEMS.map((item) => (
          <ButtonBase component={Link} key={item.to} to={item.to} aria-current={active(item.to) ? "page" : undefined}
            sx={{ minHeight: 56, gap: 0.5, flexDirection: "column", fontSize: 10, fontWeight: 700, borderRadius: "14px", color: active(item.to) ? "var(--color-green-500)" : "var(--color-text-sub2)", bgcolor: active(item.to) ? "var(--color-green-100)" : "transparent" }}>
            <PhosphorIcon name={item.icon} size={22} />{item.label}
          </ButtonBase>
        ))}
        <ButtonBase onClick={() => setNavOpen(true)} aria-expanded={navOpen} aria-controls={navOpen ? "app-navigation" : undefined}
          sx={{ minHeight: 56, gap: 0.5, flexDirection: "column", fontSize: 10, fontWeight: 700, borderRadius: "14px", color: moreActive ? "var(--color-green-500)" : "var(--color-text-sub2)", bgcolor: moreActive ? "var(--color-green-100)" : "transparent" }}>
          <PhosphorIcon name="ph ph-dots-three-outline" size={22} />その他
        </ButtonBase>
      </Box>

      <Drawer anchor="left" open={navOpen} onClose={() => setNavOpen(false)} slotProps={{ paper: { sx: { width: 320, maxWidth: "calc(100vw - 24px)", borderRadius: "0 28px 28px 0", p: 2 } } }}>
        <Box id="app-navigation" component="nav" aria-label="すべてのメニュー">
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
            <Typography sx={{ fontWeight: 800, fontSize: 20 }}>メニュー</Typography>
            <IconButton aria-label="メニューを閉じる" onClick={() => setNavOpen(false)}><PhosphorIcon name="ph ph-x" size={20} /></IconButton>
          </Box>
          <Box sx={{ p: 2, mb: 2, borderRadius: "18px", bgcolor: "var(--color-purple-100)" }}>
            <Typography sx={{ fontWeight: 700, overflowWrap: "anywhere" }}>{user.displayName}</Typography>
            <Typography variant="body2" color="text.secondary">{ROLE_LABEL[user.role]}</Typography>
          </Box>
          <List disablePadding>
            {navItems.map((item) => (
              <ListItemButton key={item.to} component={Link} to={item.to} onClick={() => setNavOpen(false)} aria-current={active(item.to) ? "page" : undefined} selected={active(item.to)}
                sx={{ minHeight: 52, gap: 1.5, mb: 0.5, px: 2, borderRadius: "14px", fontWeight: 700, fontSize: 14, color: active(item.to) ? "var(--color-green-500)" : "var(--color-text)", "&.Mui-selected": { bgcolor: "var(--color-green-100)" } }}>
                <PhosphorIcon name={item.icon} size={22} />{item.label}
                <Box sx={{ ml: "auto", color: "var(--color-text-sub)" }}><PhosphorIcon name="ph ph-caret-right" size={14} /></Box>
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>
    </>
  );
}
