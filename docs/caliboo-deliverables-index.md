# Caliboo 成果物索引（最新版）

**対象**：Caliboo（キャリブー）社内展開提案・発表・質疑応答・公開体験  
**正本**：`takeuchi-atsuki/caliboo` の `docs/caliboo-proposal-materials` ブランチ  
**確認日**：2026-11-26

このページは Codex で Caliboo の作業を継続するための入口。印刷・配布はPDF、原稿の改訂はMarkdown、画像やHTMLは該当する最新版を使用する。旧版は履歴として保持し、正本のブランチを変更しない限り、下記の相対リンクから最新版として確認した成果物にアクセスできる。

## 1. 印刷・配布用資料

| 成果物 | 印刷用PDF | 編集・プレビュー |
| --- | --- | --- |
| ポスター v4 | [PDF](caliboo-poster-v4.pdf) | [HTML](caliboo-poster-v4.html)・[PNG](caliboo-poster-v4.png) |
| パンフレット v3 | [PDF](caliboo-pamphlet-v3.pdf) | [HTML](caliboo-pamphlet-v3.html)・[表面PNG](caliboo-pamphlet-v3-front.png)・[裏面PNG](caliboo-pamphlet-v3-back.png) |
| POP v3（QRコードあり） | [PDF](caliboo-pop-v3-qr.pdf) | [HTML](caliboo-pop-v3-qr.html)・[PNG](caliboo-pop-v3-qr.png) |
| POP v3（QRコードなし） | [PDF](caliboo-pop-v3.pdf) | [HTML](caliboo-pop-v3.html)・[PNG](caliboo-pop-v3.png) |

## 2. 公式ブランド・ロゴ

[ブランド資産フォルダ](caliboo-brand/)・[ロゴキットの説明](caliboo-brand/README.md)

| 用途 | ファイル |
| --- | --- |
| 公式ワードマーク | [SVG](caliboo-brand/caliboo-wordmark.svg)・[透過PNG](caliboo-brand/caliboo-wordmark.png) |
| アプリアイコン | [SVG](caliboo-brand/caliboo-app-icon.svg)・[PNG](caliboo-brand/caliboo-app-icon.png)・[不透明PNG](caliboo-brand/caliboo-app-icon-opaque.png) |
| 使用ガイド | [ロゴガイドPDF](caliboo-brand/caliboo-logo-guide.pdf) |
| 一括取得 | [ロゴキットZIP](caliboo-brand/caliboo-logo-kit.zip) |

## 3. 発表原稿 v4（10分枠・全10枚）

| 発表案 | 原稿 | 通常稿の読み上げ音声 | 全10枚の短縮稿音声 |
| --- | --- | --- | --- |
| A案：根拠と進め方を伝える | [Markdown](caliboo-presentation-v4-a.md)・[PDF](caliboo-presentation-v4-a.pdf) | [MP3](caliboo-presentation-v4-a.mp3)（9:18） | [MP3](caliboo-presentation-v4-a-short.mp3)（5:29） |
| B案：二つのメッセージを届ける | [Markdown](caliboo-presentation-v4-b.md)・[PDF](caliboo-presentation-v4-b.pdf) | [MP3](caliboo-presentation-v4-b.mp3)（9:12） | [MP3](caliboo-presentation-v4-b-short.mp3)（5:26） |

- [v4の比較・独立レビュー・想定質疑応答](caliboo-presentation-v4-review.md)
- 想定質疑応答集（24問・2026-11-26版）：[Markdown](caliboo-presentation-qa.md)・[PDF](caliboo-presentation-qa.pdf)
- 通常稿の合成音声書き出し後の実測は、A案 9分18.48秒、B案 9分11.76秒。短縮稿はA案 5分28.80秒、B案 5分25.73秒。間と操作時間を含む。竹内本人の実演時間ではない。
- 発表本編は投影10枚で完結し、実機デモは質疑応答用とする。

## 4. 質疑応答用・実機デモ v2

[実機デモフォルダ](caliboo-qa-demo-v2/)・[実機の再現手順・検証結果](caliboo-qa-demo-v2/README.md)

- 質疑応答時の画面説明：[実機画面PDF（A4横7ページ）](caliboo-qa-demo-v2/caliboo-qa-demo-v2-screens.pdf)・[HTML](caliboo-qa-demo-v2/caliboo-qa-demo-v2-screens.html)
- 確認の根拠：[独立AIの初回解析JSON](caliboo-qa-demo-v2/04-ai-analysis-result.json)・[見出し推敲後JSON](caliboo-qa-demo-v2/04-ai-analysis-refined.json)・[取込結果](caliboo-qa-demo-v2/05-import-response.json)・[承認前の本人表示](caliboo-qa-demo-v2/06-member-before-approval.json)・[講師ロールの模擬承認](caliboo-qa-demo-v2/07-simulated-approvals.json)・[承認後の本人表示](caliboo-qa-demo-v2/08-member-after-approval.json)
- 再現用：[マニフェスト](caliboo-qa-demo-v2/manifest.json)・[再現スクリプト](caliboo-qa-demo-v2/replay_demo.py)・[別隔離DBでの再現ログ](caliboo-qa-demo-v2/10-replay-verification.txt)

架空の日報2件を現行の実アプリへ提出し、独立Codex AIで解析した出力を manual モードで本体に取り込む。v2の検証記録では、取込3候補・承認前の本人表示0件・講師ロールによる模擬承認3件・承認後の本人画面とホームへの3件反映を確認済み。再現時は収録済みAI出力を取り込み、新たなAI推論は行わない。外部AI実API接続、実日報での妥当性、教育効果は未検証。

## 5. 公開体験デモ（無料URL・静的版）

- 公開URL：[Caliboo 公開体験デモ](https://caliboo-learning-demo.steepgoby2.chatgpt.site/)
- [公開デモフォルダ](caliboo-public-demo/)・[公開版の説明・操作手順](caliboo-public-demo/README.md)
- オフライン閲覧用ソース：[index.html](caliboo-public-demo/index.html)・[style.css](caliboo-public-demo/style.css)・[demo.js](caliboo-public-demo/demo.js)

公開版は架空の日報と独立AIの固定収録済み解析結果を再現する静的デモ。新規AI推論・データの永続化・本体への接続は行わない。実機そのものや本番研修サービスとは区別する。公開時は既存のChatGPT利用枠内で、追加料金・外部API契約なし。

## 6. 最新仕様・共通メッセージ

- 製品の位置付け：キャリブレーション型教育ツール。
- 目標：「3か月で新入社員を戦力化する」。実証済み効果や達成保証とは扱わない。
- 仕組み：AIによる強み解析と創出 → 新入社員へのフィードバック。日報・課題を根拠に候補を言語化し、講師による確認・承認を経て本人へ表示する。
- 推進方針：本人（竹内）主導PoC、展開時に部署・情シス等へ相談。利用を許可された日報の範囲で初期検証（20件を目標）し、展開に向け条件を整える。
- ブランドの約束：「あなただからできることを見つけ、ミライへ飛び続けるための翼となる」。
- 現行の目的は育成。実日報を使う前に利用許可・閲覧範囲・APIの返却情報などを確認する。

## 7. Codex 作業の引き継ぎ

- 以前の発表原稿関連 Codex セッションID：`6b06d29c-8668-83ec-af43-542c480a0033`（関連作業への参照。セッションは削除・移動しない）。
- 次回の作業はこの索引を開き、正本ブランチの対象ファイルを確認してから着手する。版が更新された場合は最新版へのリンクと確認結果を更新する。
- 索引作成時は既存のPDF・HTML・PNG・音声・ZIPおよびその他の成果物を変更せず、mainへのマージは行わない。

## 8. 確認範囲

2026-11-25、GitHub 正本ブランチ上の索引先ファイル・フォルダの存在を確認し、各README・v4レビュー・再現ログの記述を照合した。公開URLへのHTTPアクセスも確認した。バイナリ成果物の再生成・再計測や実機操作の再実行は行わず、音声時間・実機操作結果は既存の検証記録から引用している。
