import { useState } from "react";
import { Alert, Button, Checkbox, FormControlLabel, Stack, TextField, Typography } from "@mui/material";
import { useResource } from "../../lib/useResource";

type CaseSummary = { id: number; reportId: number; status: string };
interface HoldoutCase extends CaseSummary {
  materials: { sources: { id: string; text: string }[] };
  materialsDigest: string;
  labelCount: number;
  ownLabelSubmitted: boolean;
  result: unknown | null;
  labels: { reviewerId: number; skillCodes: string[]; comment: string; match: string | null;
    accepted: boolean | null; acceptanceComment: string | null }[];
}

export function HoldoutEvaluation({ reviewerId }: { reviewerId: number }) {
  const cases = useResource<{ cases: CaseSummary[] }>("/api/development/holdout/cases");
  const [reportId, setReportId] = useState("");
  const parsedReportId = Number(reportId.match(/^(?:rpt_[0-9]{8}_)?([1-9][0-9]*)$/)?.[1] ?? 0);
  const [confirmed, setConfirmed] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  return <Stack spacing={2}>
    <Alert severity="info">実日報の評価には、解析結果を見ていない異なる2名の講師が必要です。合成データは実績に含めません。</Alert>
    <TextField label="評価に使う提出済み日報ID" helperText="提出完了時の日報ID（rpt_から始まる値）または材料の数値ID" value={reportId} onChange={(e) => setReportId(e.target.value)} />
    <FormControlLabel control={<Checkbox checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />}
      label="実日報であり、評価者2名が解析結果を見ていないことを確認した" />
    <Button disabled={cases.busy || !confirmed || !Number.isSafeInteger(parsedReportId) || parsedReportId <= 0}
      onClick={() => void cases.act("/api/development/holdout/cases", { reportId: parsedReportId, realAndUnseen: true })}>評価材料を固定する</Button>
    <Button onClick={() => void cases.reload()}>評価ケースを更新</Button>
    {cases.error && <Alert severity="error">{cases.error}</Alert>}
    {cases.data?.cases.map((item) => <Button key={item.id} onClick={() => setSelected(item.id)}>
      評価 #{item.id} / 日報 #{item.reportId} / {item.status === "labeling" ? "独立ラベル受付" : "受容性の確認"}
    </Button>)}
    {selected !== null && <CaseForm key={selected} caseId={selected} reviewerId={reviewerId} />}
  </Stack>;
}

function CaseForm({ caseId, reviewerId }: { caseId: number; reviewerId: number }) {
  const path = `/api/development/holdout/cases/${caseId}`;
  const resource = useResource<HoldoutCase>(path);
  const [codes, setCodes] = useState("");
  const [comment, setComment] = useState("");
  const [unseen, setUnseen] = useState(false);
  const [resultJson, setResultJson] = useState("");
  const [parseError, setParseError] = useState(false);
  const [acceptanceComment, setAcceptanceComment] = useState("");
  const item = resource.data;
  const own = item?.labels.find((label) => label.reviewerId === reviewerId);
  const saveResult = () => {
    try {
      const result: unknown = JSON.parse(resultJson);
      setParseError(false);
      void resource.act(`${path}/result`, { materialsDigest: item!.materialsDigest, result });
    } catch { setParseError(true); }
  };
  return <Stack spacing={2}>
    <Typography component="h3" variant="h6">評価 #{caseId}</Typography>
    <Button onClick={() => void resource.reload()}>選択した評価を更新</Button>
    {resource.error && <Alert severity="error">{resource.error}</Alert>}
    {item && <>
      <Typography>独立ラベル: {item.labelCount}/2名</Typography>
      {item.materials.sources.map((source) => <Typography key={source.id} sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{source.id}: {source.text}</Typography>)}
      <Typography sx={{ overflowWrap: "anywhere" }}>材料SHA-256: {item.materialsDigest}</Typography>
      <details><summary>解析担当者向けの凍結材料JSON</summary><Typography component="pre" sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(item.materials, null, 2)}</Typography></details>
      {!item.ownLabelSubmitted && item.labelCount < 2 && <>
        <TextField label="独立に判断したスキルコード（カンマ区切り、該当なしは空欄）" value={codes} onChange={(e) => setCodes(e.target.value)} />
        <TextField label="判断の理由" multiline value={comment} onChange={(e) => setComment(e.target.value)} />
        <FormControlLabel control={<Checkbox checked={unseen} onChange={(e) => setUnseen(e.target.checked)} />} label="解析結果や他の評価者のラベルを見ていない" />
        <Button disabled={resource.busy || !unseen || !comment.trim()} onClick={() => void resource.act(`${path}/labels`, {
          skillCodes: codes.split(",").map((code) => code.trim()).filter(Boolean), comment, outputUnseen: true,
        })}>独立ラベルを確定する（変更不可）</Button>
      </>}
      {item.ownLabelSubmitted && <Typography>あなたの独立ラベルは確定済みです。</Typography>}
      {item.labelCount === 2 && item.result === null && <>
        <Typography>2名のラベルが確定しました。凍結材料を解析した結果を登録してください。</Typography>
        <TextField label="解析結果JSON" multiline minRows={4} value={resultJson} onChange={(e) => setResultJson(e.target.value)} />
        <Button disabled={resource.busy || !resultJson.trim()} onClick={saveResult}>解析結果を固定する（変更不可）</Button>
        {parseError && <Alert severity="error">JSONの形式を確認してください。入力は保持されています。</Alert>}
      </>}
      {item.result !== null && <>
        <Typography component="pre" sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(item.result, null, 2)}</Typography>
        {item.labels.map((label) => <Typography key={label.reviewerId}>
          評価者 #{label.reviewerId}: {label.skillCodes.join(", ") || "該当なし"} / {label.match} / {label.comment}
          {label.accepted !== null && ` / ${label.accepted ? "受容" : "改善が必要"}: ${label.acceptanceComment}`}
        </Typography>)}
        {own?.accepted === null && <>
          <TextField label="結果を確認した理由" multiline value={acceptanceComment} onChange={(e) => setAcceptanceComment(e.target.value)} />
          {[true, false].map((accepted) => <Button key={String(accepted)} disabled={resource.busy || !acceptanceComment.trim()}
            onClick={() => void resource.act(`${path}/acceptance`, { accepted, comment: acceptanceComment })}>
            {accepted ? "受容して確定" : "改善が必要として確定"}</Button>)}
        </>}
      </>}
    </>}
  </Stack>;
}
