# Caliboo 公開体験デモ（静的版）

2026-11-25 暫定公開。  
**公開URL:** <https://caliboo-learning-demo.steepgoby2.chatgpt.site/>

## 目的と範囲

質疑応答または別端末からの試用向けに、日報→強み候補→講師承認→本人表示までを約2分で体験する独立した静的デモ。本番アプリではなく、事前に作った架空日報2件と、別のCodex解析セッションが実際に生成した2件の候補を固定収録している。アクセスした端末でAIを呼び出す処理ではない。

- 新規アカウント、入力保存、実在データの登録、外部モデル通信なし。架空日報の入力ボタンは固定値を表示するだけ。
- 講師には根拠を表示。選択・承認した候補だけを本人に表示し、本人表示では原文引用を表示しない。
- 別の端末・ブラウザからログインなしで閲覧可能（公開アクセス）。
- 個人情報、社内資料、実日報、APIキー、データベースを公開していない。サイトは本体のデータ・APIと接続しない。ページに検索インデックスを抑える指示はあるが、公開URLを知った人は閲覧・共有できる。

## 操作手順

1. 「架空の日報を入力」を押し、Keep / Problem / Tryを確認。
2. 「日報を提出する（体験）」→「解析例を表示」。
3. 「講師の確認へ」から原文根拠・評価の範囲を確認し、承認する候補を選択。
4. 「選択した候補を承認し、本人へ表示（体験）」から強みと次の一歩を確認。
5. 「もう一度体験する」で初期化。

## GitHub Pagesの調査結果

[CalibooのGitHubリポジトリ](https://github.com/takeuchi-atsuki/caliboo)は既に公開設定。標準のGitHub Pagesを無料で利用できるが、PagesはHTML/CSS/JavaScriptの静的ホスティングであり、本体のFastAPI・SQLite・Cookieによる認証/APIを実行できない。

本体をそのまま公開する手段には適さない。別途Pagesを使う場合は、このデモの `index.html`、`style.css`、`demo.js` だけを格納する専用リポジトリ、または他の資料を含まない専用配信アーティファクトに限定する。GitHubのSettings > Pagesで配信元を設定すれば閲覧URLを発行できる。既存Calibooのリポジトリ設定やPages設定は変更していない。

- [GitHub Pagesについて（GitHub公式）](https://docs.github.com/ja/pages/getting-started-with-github-pages/what-is-github-pages)
- [配信元の設定（GitHub公式）](https://docs.github.com/ja/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## 暫定公開の運用

ChatGPT Sitesを使用。Plus・Proのホスティングは公式FAQにおいて現在プランに含まれており、今回のサイトは静的配信のみ。追加料金プラン、外部API、独自ドメイン、外部サービスの契約はしていない。既存のChatGPT利用枠内で構築。

- [ChatGPT Sitesの仕様・料金・共有設定（OpenAI公式）](https://help.openai.com/en/articles/20001339-creating-and-using-chatgpt-sites)
- 公開を終了するときは、ChatGPTのSitesから「Caliboo｜公開体験デモ」の共有をオーナーのみに戻す。リンクを共有済みの場合でも公開アクセスを絞れるが、既に保存・複製された内容の回収はできない。

## 動作確認（2026-11-25）

- Chromiumローカルプレビュー：日報入力・提出・候補表示・2件承認・本人表示・初期化成功。スクリーン上でレイアウト確認。
- 公開URL：認証情報・CookieなしのHTTP GETでHTML、CSS、JSすべて200。配信ソースとローカルファイルのハッシュ一致。
- 公開URLのブラウザ操作：1件のみ選んだ状態では本人表示も1件のみ。本人画面に原文引用なし。初期化確認済み。
- iPhone実機・実本体のリアルタイムAPIを用いた解析の確認は本静的デモの範囲外。
- ここでの候補は架空日報からのAI推定であり、教育効果・能力の実証値ではない。

## オフラインで開く

同じフォルダに `index.html`、`style.css`、`demo.js` を置き、`index.html` をブラウザで開く。
