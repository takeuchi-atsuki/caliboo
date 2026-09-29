import { describe, expect, it } from "vitest";
import { summarizeStrength } from "./strengthSummary";

describe("ホームの強み要約 (docs/screens/home.md)", () => {
  it.each([
    ["NULLと提出行の有無を区別したSQLの作成・実行", "SQLが得意"],
    ["誤判定しやすい境界を検証に落とす", "境界の検証が得意"],
    ["欠損の意味を分けて集計する", "欠損データの集計が得意"],
    ["利用条件を処理の流れに組み込む", "条件を考慮した実装が得意"],
    ["実行条件と期待値・実測値の記録", "検証結果の記録が得意"],
    ["セッション認証と出力整形を備えたAPI利用スクリプトの実装", "API連携の実装が得意"],
    ["期待値照合と異常系を含む成果物の検証", "異常系の検証が得意"],
  ])("%s の要点を表示する", (label, expected) => {
    expect(summarizeStrength({ label, kind: "ability" })).toEqual({ label: expected, isAiPoc: false });
  });

  it("旧形式も扱い、AI作業PoCの出典を保持する", () => {
    expect(summarizeStrength({ label: "【AI作業PoC】 SQLの作成・実行" })).toEqual({ label: "SQLが得意", isAiPoc: true });
  });

  it("仕事の進め方は能力として断定しない", () => {
    expect(summarizeStrength({ label: "成果を別の確かめ方でも確認する", kind: "work_style" }).label).toBe("多角的に確かめる");
    expect(summarizeStrength({ label: "SQLの作成を慎重に確認する", kind: "work_style" }).label).toBe("SQLの作成を慎重に確認する");
  });

  it.each([
    "課題を整理する力", "慎重に確かめるタイプ", "独自の長い表現でも意味を削らずに承認済みの見出しを残す",
    "SQLの作成はまだ得意ではない", "境界の検証には課題が残る", "欠損の集計は苦手",
  ])("対応しない表現や留保は原文を保持する: %s", (label) => {
    expect(summarizeStrength({ label }).label).toBe(label);
  });
});
