import type { StrengthKind } from "../../lib/types";

type SummaryRule = { pattern: RegExp; label: string };

// !NOTE: 承認済みの見出しで明示された内容だけを短くする表示用の言い換え。
// 解釈・引用中の単語から新しい強みを推測せず、対応しない表現は原文を残す。
const abilityRules: SummaryRule[] = [
  { pattern: /SQL(?:の)?(?:作成|実行|集計)/i, label: "SQLが得意" },
  { pattern: /境界.*(?:検証|テスト|分析)/, label: "境界の検証が得意" },
  { pattern: /欠損.*集計/, label: "欠損データの集計が得意" },
  { pattern: /利用条件.*(?:流れ|処理).*組み込/, label: "条件を考慮した実装が得意" },
  { pattern: /(?:実行条件|期待値|実測値).*記録/, label: "検証結果の記録が得意" },
  { pattern: /API.*スクリプト.*実装/i, label: "API連携の実装が得意" },
  { pattern: /期待値.*異常系.*検証/, label: "異常系の検証が得意" },
];

const workStyleRules: SummaryRule[] = [
  { pattern: /(?:成果|結果).*別の確かめ方.*確認/, label: "多角的に確かめる" },
];

export function summarizeStrength(strength: { label: string; kind?: StrengthKind }) {
  const isAiPoc = strength.label.startsWith("【AI作業PoC】");
  const original = strength.label.replace(/^【AI作業PoC】\s*/, "").trim();
  const rules = strength.kind === "work_style" ? workStyleRules : abilityRules;
  // !NOTE: 否定・留保を含む見出しを「得意」と断定する言い換えにはしない。
  const qualified = /ない|苦手|不足|未|課題|不十分|要改善|とは限ら|ではなく/.test(original);
  const label = qualified ? original : rules.find((rule) => rule.pattern.test(original))?.label ?? original;
  return { label, isAiPoc };
}
