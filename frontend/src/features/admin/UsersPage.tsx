import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Alert, Box, Button, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useAuth } from "../../components/auth/AuthProvider";
import { PageContainer } from "../../components/layout/PageContainer";
import { useResource } from "../../lib/useResource";
import type { Department, ManagedUser } from "../../lib/types";

export function UsersPage() {
  const { user } = useAuth();
  const resource = useResource<{ users: ManagedUser[] }>(user?.role === "admin" ? "/api/users" : null);
  const departments = useResource<{ departments: Department[] }>("/api/ojt/departments");
  const [selected, setSelected] = useState<ManagedUser | null>(null);
  const [filter, setFilter] = useState("");
  if (user?.role !== "admin") return <Navigate to="/home" replace />;
  return <PageContainer><Stack spacing={3} sx={{ p: { xs: 2, md: 4 } }}>
    <Typography variant="h5" component="h1">ユーザー管理</Typography>
    {resource.error && <Alert severity="error">{resource.error}</Alert>}
    <Button onClick={() => void resource.reload()}>再読み込み</Button>
    <TextField select label="配属で絞り込む" value={filter} onChange={(e) => setFilter(e.target.value)}>
      <MenuItem value="">すべて</MenuItem>
      {departments.data?.departments.map((dept) => <MenuItem key={dept.id} value={dept.id}>{dept.name}</MenuItem>)}
    </TextField>
    <Stack direction="row" useFlexGap sx={{ flexWrap: "wrap", gap: 1 }}>
      <Button variant="outlined" onClick={() => setSelected(null)}>新しいユーザー</Button>
      {resource.data?.users.filter((item) => !filter || item.departmentId === filter).map((item) =>
        <Button key={item.id} onClick={() => setSelected(item)}>{item.displayName}{item.active ? "" : "（無効）"}</Button>)}
    </Stack>
    <UserEditor key={selected?.id ?? "new"} selected={selected} departments={departments.data?.departments ?? []}
      busy={resource.busy} save={async (body) => {
        const ok = await resource.act(selected ? `/api/users/${selected.id}` : "/api/users", body);
        if (ok) setSelected(null);
        return ok;
      }} />
  </Stack></PageContainer>;
}

function UserEditor({ selected, departments, busy, save }: {
  selected: ManagedUser | null; departments: Department[]; busy: boolean;
  save: (body: unknown) => Promise<boolean>;
}) {
  const [loginId, setLoginId] = useState("");
  const [displayName, setDisplayName] = useState(selected?.displayName ?? "");
  const [role, setRole] = useState(selected?.role ?? "member");
  const [active, setActive] = useState(selected?.active ?? true);
  const [departmentId, setDepartmentId] = useState(selected?.departmentId ?? "");
  const [password, setPassword] = useState("");
  const [saved, setSaved] = useState(false);
  return <Box component="form" onSubmit={async (event) => {
    event.preventDefault();
    const ok = await save({ loginId, displayName, role, active, departmentId: departmentId || null,
      ...(!selected || password ? { password } : {}) });
    if (ok) { setPassword(""); setSaved(true); }
  }}><Stack spacing={2} sx={{ maxWidth: 600 }}>
    <Typography component="h2" variant="h6">{selected ? `${selected.displayName}を編集` : "ユーザーを作成"}</Typography>
    {saved && <Alert severity="success">保存しました</Alert>}
    {!selected && <TextField required label="ログインID" value={loginId} onChange={(e) => setLoginId(e.target.value)} />}
    <TextField required label="表示名" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
    <TextField select label="ロール" value={role} onChange={(e) => setRole(e.target.value as ManagedUser["role"])}>
      <MenuItem value="member">新入社員</MenuItem><MenuItem value="admin">講師</MenuItem>
    </TextField>
    <TextField select label="配属" value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
      <MenuItem value="">未配属</MenuItem>
      {departments.map((dept) => <MenuItem key={dept.id} value={dept.id}>{dept.name}</MenuItem>)}
    </TextField>
    {selected && <TextField select label="アカウント" value={String(active)} onChange={(e) => setActive(e.target.value === "true")}>
      <MenuItem value="true">有効</MenuItem><MenuItem value="false">無効</MenuItem>
    </TextField>}
    <TextField label={selected ? "新しいパスワード（変更時のみ）" : "パスワード"} type="password" autoComplete="new-password"
      required={!selected} value={password} onChange={(e) => setPassword(e.target.value)}
      slotProps={{ htmlInput: { minLength: 12, maxLength: 128 } }} helperText="12〜128文字" />
    <Button type="submit" variant="contained" disabled={busy}>保存</Button>
    {selected?.history.map((entry, index) => <Typography key={index} variant="body2">
      {entry.changedAt}: {departments.find((dept) => dept.id === entry.departmentId)?.name ?? "未配属"}
    </Typography>)}
  </Stack></Box>;
}
