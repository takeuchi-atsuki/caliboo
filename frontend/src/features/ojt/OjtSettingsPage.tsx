import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Alert, Box, Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useAuth } from "../../components/auth/AuthProvider";
import { PageContainer } from "../../components/layout/PageContainer";
import { useResource } from "../../lib/useResource";
import type { Department, OjtConfiguration } from "../../lib/types";
import { useOjtConfiguration } from "./useOjtConfiguration";

const ICONS = [
  ["ph ph-code", "コード"], ["ph ph-shield-check", "品質"], ["ph ph-handshake", "営業"],
  ["ph ph-compass-tool", "設計"], ["ph ph-factory", "製造"], ["ph ph-briefcase", "業務"],
];
const COLORS = [
  ["#d6ebff", "青"], ["#cdeede", "緑"], ["#ffd9e6", "ピンク"],
  ["#e3ddff", "紫"], ["#ffe9c7", "オレンジ"], ["#f4f0ec", "グレー"],
];

export function OjtSettingsPage() {
  const { user } = useAuth();
  if (user?.role !== "admin") return <Navigate to="/home" replace />;
  return <OjtSettingsEditor />;
}

function OjtSettingsEditor() {
  const departments = useResource<{ departments: Department[] }>("/api/ojt/departments");
  const [departmentId, setDepartmentId] = useState("");
  const [notice, setNotice] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const form = useOjtConfiguration(departmentId);
  const { draft } = form;
  const disabled = form.loading || form.saving || refreshing;
  const edit = <K extends keyof OjtConfiguration>(key: K, value: OjtConfiguration[K]) => {
    setNotice(false);
    form.setDraft((previous) => previous && { ...previous, [key]: value });
  };

  return <PageContainer><Stack spacing={3} sx={{ p: { xs: 2, md: 3 }, width: "100%", minWidth: 0, maxWidth: 900, mx: "auto", overflowWrap: "anywhere" }}>
    <Typography component="h1" variant="h5">部署別OJT設定</Typography>
    <Typography>部署ごとに相談の案内とナレッジを設定します。講師はすべての部署を編集できます。</Typography>
    {departments.error && <Alert severity="error" action={<Button onClick={() => void departments.reload()}>一覧を再取得</Button>}>{departments.error}</Alert>}
    <TextField select label="編集する部署" value={departmentId} disabled={disabled}
      helperText="部署を切り替えると未保存の変更は破棄されます。"
      onChange={(event) => { setNotice(false); setDepartmentId(event.target.value); }}>
      <MenuItem value="">新しい部署を追加</MenuItem>
      {departments.data?.departments.map((dept) => <MenuItem key={dept.id} value={dept.id} sx={{ whiteSpace: "normal", overflowWrap: "anywhere" }}>{dept.name}</MenuItem>)}
    </TextField>
    {form.error && <Alert severity="error">{form.error}</Alert>}
    {notice && <Alert severity="success">設定を保存しました。OJT画面を開き直すと反映されます。</Alert>}
    {departmentId && <Button disabled={disabled} onClick={() => void form.reload()}>最新の設定を読み直す（入力を破棄）</Button>}
    {form.loading && <Typography role="status">設定を読み込んでいます。</Typography>}
    {draft && <Box component="form" onSubmit={async (event) => {
      event.preventDefault();
      setNotice(false);
      setRefreshing(true);
      const result = await form.save();
      if (result) { await departments.reload(); setDepartmentId(result.id); setNotice(true); }
      setRefreshing(false);
    }}>
      <Box component="fieldset" disabled={disabled} sx={{ border: 0, p: 0, m: 0, minWidth: 0 }}><Stack spacing={2}>
        <TextField label="部署ID" required value={draft.id} disabled={Boolean(departmentId)}
          onChange={(event) => edit("id", event.target.value)}
          slotProps={{ htmlInput: { pattern: "[a-z][a-z0-9-]{0,39}", maxLength: 40 } }} helperText="英小文字から始まる英小文字・数字・ハイフン。作成後は変更できません。" />
        <TextField label="部署名" required value={draft.name} onChange={(event) => edit("name", event.target.value)} slotProps={{ htmlInput: { maxLength: 100 } }} />
        <TextField select disabled={disabled} label="アイコン" value={draft.icon} onChange={(event) => edit("icon", event.target.value)}>
          {ICONS.map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
        </TextField>
        <TextField select disabled={disabled} label="色" value={draft.color} onChange={(event) => edit("color", event.target.value)}>
          {COLORS.map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
        </TextField>
        <TextField label="初期案内" required multiline minRows={3} value={draft.welcomeMessage}
          onChange={(event) => edit("welcomeMessage", event.target.value)} slotProps={{ htmlInput: { maxLength: 4000 } }} />
        <TextField label="回答の補足案内" multiline minRows={2} value={draft.replyGuidance}
          onChange={(event) => edit("replyGuidance", event.target.value)} slotProps={{ htmlInput: { maxLength: 4000 } }}
          helperText="テンプレート回答の末尾に表示する文章です。AIへの指示ではありません。" />
        <Typography component="h2" variant="h6">質問候補（最大8件）</Typography>
        {draft.quickAsks.map((question, index) => <Stack key={index} direction="row" spacing={1}>
          <TextField fullWidth required label={`質問候補 ${index + 1}`} value={question} slotProps={{ htmlInput: { maxLength: 200 } }}
            onChange={(event) => edit("quickAsks", draft.quickAsks.map((item, at) => at === index ? event.target.value : item))} />
          <Button aria-label={`質問候補 ${index + 1}を削除`} onClick={() => edit("quickAsks", draft.quickAsks.filter((_item, at) => at !== index))}>削除</Button>
        </Stack>)}
        <Button disabled={draft.quickAsks.length >= 8} onClick={() => edit("quickAsks", [...draft.quickAsks, ""])}>質問候補を追加</Button>
        <Typography component="h2" variant="h6">ナレッジ（{draft.knowledge.length}件 / 最大100件）</Typography>
        <Typography variant="body2">参照一覧に表示する資料の案内です。登録だけで自動回答の検索・学習は行われません。</Typography>
        {draft.knowledge.map((item, index) => <Paper key={index} variant="outlined" sx={{ p: 2 }}><Stack spacing={2}>
          <TextField required label={`ナレッジ ${index + 1}のタイトル`} value={item.title} slotProps={{ htmlInput: { maxLength: 200 } }}
            onChange={(event) => edit("knowledge", draft.knowledge.map((value, at) => at === index ? { ...value, title: event.target.value } : value))} />
          <TextField required multiline label={`ナレッジ ${index + 1}の説明`} value={item.description} slotProps={{ htmlInput: { maxLength: 4000 } }}
            onChange={(event) => edit("knowledge", draft.knowledge.map((value, at) => at === index ? { ...value, description: event.target.value } : value))} />
          <Button onClick={() => edit("knowledge", draft.knowledge.filter((_value, at) => at !== index))}>ナレッジ {index + 1}を削除</Button>
        </Stack></Paper>)}
        <Button disabled={draft.knowledge.length >= 100} onClick={() => edit("knowledge", [...draft.knowledge, { title: "", description: "" }])}>ナレッジを追加</Button>
        <Button type="submit" variant="contained">{form.saving ? "保存中…" : "設定を保存"}</Button>
      </Stack></Box>
    </Box>}
  </Stack></PageContainer>;
}
