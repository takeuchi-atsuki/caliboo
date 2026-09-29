# Caliboo アーキテクチャ概要

## 目的

新人研修向けパーソナライズ学習ツール「Caliboo」のフロントエンド6画面（デザインカンプ由来）と、それを動かすためのダミーバックエンドAPIを実装する。

!NOTE: 課題演習画面(`/assignments`、`docs/screens/assignment.md`)はデザインカンプ由来ではなく、後から追加した7画面目。

## 全体構成

```
frontend/  React + TypeScript + Vite（画面）
backend/   FastAPI（SQLiteでDB永続化するAPI）
docs/      本ディレクトリ（仕様書）
```

バックエンドはSQLiteでDB永続化を行う。DB本体は`backend/var/caliboo.db`(`CALIBOO_SQLITE_PATH`環境変数で変更可能)に保存され、アプリ起動時(`main.py`の`lifespan`)に`init_engine()`→`bootstrap_db()`でテーブル作成・初回シード投入を行う。`POST /api/report`等の書き込み系エンドポイントは、DBの`reports`テーブルへINSERTする。`GET /api/report/history`により、提出済み日報の全文(Keep/Problem/Try/きもち/きもちコメント)を一覧取得できる。下書き(`status: "draft"`)は`GET /api/report/drafts`で一覧取得・`DELETE /api/report/drafts/{id}`で削除でき、一覧から選んだ内容をフロントのフォームへ反映することで編集を実現している(専用の更新APIは無く、編集後の再保存も既存の`POST /api/report`への新規INSERTで行う。詳細は`docs/screens/report.md`を参照)。

課題演習機能(`assignments`/`assignment_submissions`テーブル)は、講師による課題(タイトル・課題文)の作成、新入社員によるテキスト回答の提出、講師によるコメントフィードバックという一連のワークフローを永続化する(詳細は`docs/screens/assignment.md`を参照)。個人宛ての課題は`assignment_recipients`(課題ごとに0〜1行。行なし=全員宛て)で配信先と講師のひとことを持つ。AIの課題案は`assignment_proposals`に生成時の内容・分析した材料・生成器名を記録し、配信すると作成した課題を`assignment_id`で指す。既定の生成は`services/assignment_proposal/`のルールベース生成器(`RuleBasedProposalGenerator`)で行い、強み解析PoCの`providers.py`と同じくProtocolで差し替え可能にしている。

!NOTE: MySQL/PostgreSQL等の外部DBMSではなくSQLiteを選んだ理由は、DevContainerだけで完結し追加のミドルウェアインストールが不要な点(移植性)、依存関係を最小限に保つ方針、および今回のスコープが「デザイン案の動作確認」であり本格的な同時接続・スケールを想定しないためである。

!TIP: モック定数は削除せず`backend/src/caliboo_api/data/seed/`配下に保持し、`bootstrap_db()`の初回シード投入元、およびテストの固定データとして共用している(シードデータとテストフィクスチャの二重管理を避けるため)。シード投入は`departments`テーブルが空の場合のみ行われるため、既存の`caliboo.db`ファイルが残っている限り再投入されない(`assignments`/`assignment_submissions`等、後から追加したテーブルも同じ単一ゲートの対象で、テーブル自体は`create_all`で作られてもシードは投入されない)。ローカルのシード内容を最新化したい場合は`backend/var/caliboo.db`を削除してから再起動する。(例: AIの課題案の確認用に追加した新入社員ハルカとその日報(`report_seed.py`)は、DBを作り直すまで入らない)

`bootstrap_db()`はシード投入の判定より前に旧スキーマ(`users`テーブル導入前)のDBを検知する(`db.py`の`_check_schema_compatibility()`)。`home_profile`テーブルが存在し、`departments`がシード済みであるにもかかわらず「`users`が空」または「`home_profile`に`user_id`列が無い」場合を旧スキーマとみなし、`backend/var/caliboo.db`の削除を促すメッセージ付きで起動に失敗する。マイグレーションは用意していないため、旧スキーマのDBは削除して作り直す必要がある。`users`テーブル導入前のコードへ戻す場合も、同じくDBの削除が必要になる。

!NOTE: 旧スキーマを検知して起動を止めるのは、`create_all`が既存テーブルに列を追加しないため。黙って起動すると「誰もログインできない」「一部APIだけ500になる」という原因の分かりにくい状態になる。

## 認証・認可

ログインIDとパスワードによる認証と、`users.role`(`admin`/`member`)による認可をバックエンドで行う(画面仕様は`docs/screens/login.md`、API仕様は`docs/api.md`「認証」)。

```text
auth/password.py   パスワードのハッシュ化・検証(hashlib.scrypt)
auth/session.py    セッションの発行・検証・破棄(user_sessionsテーブル)
auth/deps.py       get_current_user(401) / require_admin・require_member(403)
routers/auth.py    /api/auth/login・logout・me
```

- 認証は`main.py`で`auth`以外の全ルーターに`get_current_user`を一括付与して強制する。「`/api/auth/login`・`/api/auth/logout`以外の全`/api/*`が未認証で401になる」ことは、`app.openapi()`(公開HTTP APIの定義)から`/api/*`のMethod×Pathを列挙する単体テストで担保している。
- セッションは12時間有効で、HttpOnly Cookie(`caliboo_session`、`SameSite=Lax`)で受け渡す。DBにはトークンのSHA-256ハッシュのみを保存する。`Secure`属性は`CALIBOO_COOKIE_SECURE`環境変数で有効化する(開発環境はhttpのため既定は無効)。
- 個人データ(`home_profile`・`reports`・`assignment_submissions`)は`user_id`で所有者を持つ。個人宛て課題の配信先(`assignment_recipients`)・課題案(`assignment_proposals.target_user_id`)も対象の新入社員を`user_id`で指す。資格(`certifications`)は`home_profile.certification_id`(UNIQUE)経由で1ユーザー1行になる。全ユーザーが`home_profile`を1行持つことを不変条件とする(ホーム・資格勉強のAPIがこれを前提にしているため)。

!NOTE: 認証の強制を各ルーター定義(`APIRouter(dependencies=...)`)ではなく`main.py`での一括付与にしたのは、ルーターを追加するたびに付け忘れると、その画面のAPIが未認証で公開されてしまうため。

!NOTE: トークンをlocalStorage+`Authorization`ヘッダーではなくHttpOnly Cookieで扱うのは、画面側のスクリプトからトークンを読み出せないようにし、XSSが起きた場合でもトークンを持ち出されないようにするため。Cookieを確実に送れるよう、開発環境ではViteの`server.proxy`で`/api`をバックエンドへ転送し、画面とAPIを同一オリジンにしている(別オリジンのままだと、`localhost`以外のホスト名で開いた際にクロスサイト扱いとなりCookieが送られないため)。画面とAPIが同一オリジンになるため、バックエンドはCORS設定を持たない。

!NOTE: パスワードのハッシュ化に`hashlib.scrypt`(標準ライブラリ)を使うのは、依存パッケージを増やさない方針(SQLite採用と同じ理由)のため。社内SSO(OIDC等)へ移行する場合に備え、`users.password_hash`はNULL許容、`users.external_id`(外部IDプロバイダ上のID)を予約している。

## 強み解析PoCの構成

OJTの作業ログ・日報・レビューから強みを解析する仕組み(基本仕様書: `example/Caliboo_強み解析_PoC_機能追加_基本仕様書.md`、画面: `docs/screens/strengths.md`、API: `docs/api.md`)を、既存バックエンドの1モジュールとして実装している。

```text
routers/poc_strength.py          エンドポイント(/api/poc)
data/poc_strength_data.py        DBアクセス(PocRun)
data/poc_persona_scripts.py      デモ台本(3ペルソナ)
services/poc_strength/
  pipeline.py                    ①3周ループ→②日報→③レビュー+Fan-in→④解析の連結
  providers.py                   生成・解析の差し替え可能なインターフェース
  analysis.py                    ルールベースの3層解析エンジン
  fan_in.py                      3職種レビューの統合(ルールベース)
  skill_catalog.py               スキル辞書・確信度表・育成アクション表
```

!NOTE: 独立したPoCサービスではなく既存の`caliboo_api`へ同居させたのは、FastAPI+SQLite+テスト規約(spec/impl分離)をそのまま使えて、devcontainer・CI・デプロイ経路を追加せずに済むため。PoCの規模に対して別サービスを立てる利点が無いと判断した。

!NOTE: 「生成」を担うエージェント(Run Task / OJT Trainer / 3職種レビュー)は、実行時に外部LLM APIを呼ばず、開発時にClaudeがペルソナ別に執筆した台本(`data/poc_persona_scripts.py`)を返す`AuthoredMockProvider`として実装している。このdevcontainerには`claude` CLIバイナリが無く(VS Code拡張としてのみ導入されている)、アプリケーションから実行時にClaudeを呼び出す経路が存在しないため。基本仕様書§6が求めるプロバイダ非依存の抽象化層(`providers.py`)は用意してあり、実LLM連携へ差し替える際は実装を追加するだけで済む。その際は`POST /api/poc/runs`の非同期化(基本仕様書§6が想定するジョブ投入+ポーリング)もあわせて必要になる。

!NOTE: 上記の制約は「強み解析PoCのアプリ実行時にLLMを呼ぶ経路が無い」ことのみを述べており、「開発セッションのClaude自身が生成を担い、結果をアプリへ投入する」経路までは塞いでいない。`POST /api/poc/runs/import`(`.claude/skills/caliboo-strength-run/`から起動)がその経路で、Claude Codeセッションが4種のエージェント定義(`.claude/agents/strength-*.md`)としてRun Task・OJT Trainer・3職種レビュー・解析を演じ、組み立てたtrajectory・日報・レビューを投入する。

サーバー側はFan-in統合以降(`services/poc_strength/pipeline.py`の`_assemble_run()`)を台本経由と共有するため、解析(`RuleBasedAnalysisProvider`)・確信度・循環評価回避の境界はいずれも変わらない。解析エージェント(`strength-analyst`)の結果はルールベース解析とは別に`trace.externalAnalysis`へ格納し、突き合わせ材料として保持する(仕様書§2「評価者の分離」)。

!NOTE: `trace.externalAnalysis`はDBに保存し、`/strengths/poc`でルールベース結果とスキルごとの判定・確信度を比較表示する。実日報の解析は別の永続ジョブとして管理する。

!NOTE: 解析(④)だけは台本を返すのではなく、入力テキストから根拠を抽出して確信度・判定・Will-Skill象限を算出する実際のルールベースエンジンとして実装している。基本仕様書が抽象化層を求めた最大の動機が「解析だけ別モデルに差し替える」ことであるため、解析も`AnalysisProvider`インターフェースの内側に置いている(現在の実装は`RuleBasedAnalysisProvider`)。

!NOTE: 確信度は、キーワードの出現回数ではなく「独立した裏付けの種類数(軌跡/日報/レビューのうち何種類から裏付けられたか)」だけで決める。出現回数を主軸にすると、記述量が多い人ほど確信度が高くなり、「根拠の強さ」ではなく「文章の長さ」を測ることになるため。この設計により、基本仕様書§10で未決だった「評価保留のconfidenceしきい値」が3値の表(`skill_catalog.py`)として確定した。

!NOTE: 解析には`injectedPersona`(検証用に注入した既知の強み)と`skillHint`(タスク定義が持つSFIAコード)を渡さない。答えに相当する情報を解析自身が読めると、基本仕様書§8(a)の検証が自明に通ってしまい、パイプラインの健全性を測る独立した検査として機能しなくなるため(循環評価の回避)。この境界は`tests/unit/test_poc_strength_data_impl.py`で「`injectedPersona`を書き換えても解析結果が変わらない」ことを確認して担保している。

!NOTE: スキル辞書(`skill_catalog.py`)はペルソナ台本より先に確定させる。台本を書いてからキーワードを足すと、台本に合わせて辞書を調整したトートロジーになり、検証(a)が独立した検査にならないため。同じ理由で、台本には期待値(`expectedSkillCodes`/`expectedAbsentSkillCodes`/`expectedOverallStatus`)を宣言させ、再現できているかを自動テストで機械判定している。

## フロントエンド技術選定

- React + TypeScript + Vite: デザインカンプの`sc-for`/`sc-if`繰り返し・条件表示をReactのコンポーネント・stateに素直にマッピングできるため採用。
- MUI(`@mui/material`): 業務ロジックと密結合したUI要素(資格勉強クイズの選択肢、OJT課カード等)を含む全コンポーネントで採用する。キーボード操作対応・フォーカス管理・フォーカスリング表示を自前実装すると都度作り込みが必要になるため、標準でこれらを備えるUIライブラリに委ねる方針とした。
- 色・角丸のデザイントークン(`src/styles/tokens.css`のCSS変数)は単一の色ソースとして維持し、`src/theme.ts`の`createAppTheme(mode)`から参照する。`palette.accent`は`var(--color-*)`のままモード分岐が不要だが、`palette.text`/`palette.background`はMUI内部が`alpha()`等の色演算に使うため、CSS変数参照ではなくモードごとに異なる実値をハードコードする例外としている(詳細は`src/theme.ts`のコメント参照)。
- ダークモード対応: `tokens.css`は`:root`(ライト)に加え`[data-theme="dark"]`セレクタでダーク版のCSS変数を持つ。`<html>`要素の`data-theme`属性で切り替わり、`components/theme/ThemeModeProvider.tsx`が初期値の決定(localStorage優先、無ければOS設定`prefers-color-scheme`に追従)・切替・永続化を担う。初期表示後も、まだ手動でモードを選択していない間はOS設定のライブ変更(`matchMedia`の`change`イベント)に追従し続けるが、一度でも手動選択(localStorageへの保存)が行われた後は、OS設定が変化してもそれを無視し明示選択を維持する。
- ログイン状態: `components/auth/AuthProvider.tsx`が起動時に`GET /api/auth/me`でログイン中のユーザーを取得し、`useAuth()`で各画面へ提供する。`components/auth/RequireAuth.tsx`が`/login`以外の全ルートを保護する。APIが401を返した場合(セッション期限切れ等)は`lib/apiClient.ts`の401ハンドラ経由で未ログイン状態へ戻し、`/login`へ遷移させる(`/api/auth/*`自体の401は、ログイン失敗の表示と競合させないため対象外)。
- 日報入力内容の自動保存: `features/report/reportAutosave.ts`がlocalStorage(キー`caliboo:report-autosave`)への読み書きを担う。プライベートモード等でlocalStorageが例外を投げても日報の入力・送信という本来の機能を止めないよう、読み書きをすべて`try/catch`で囲み失敗時は「自動保存なし」として扱う(テーマ設定は表示設定の保持のみで、`try/catch`は入れていない)(仕様は`docs/screens/report.md`「入力内容の自動保存・復元」参照)。
- Tailwind CSSは採用しない。アクセントカラー・角丸のユーティリティクラス生成という役割はMUIのテーマ機能と重複するため、`devDependencies`・`postcss.config.js`のプラグイン登録を外している。`tailwind.config.ts`/`postcss.config.js`のファイル自体はビルドに関与しない状態で残置されている(削除コマンドの実行権限上の制約による)。
- React Router: 画面間遷移（ホーム→強み/日報/課題/OJT/資格勉強）をURLベースで表現するため採用。

!NOTE: ダーク版の配色は単純な明度反転ではなく、色相(green/blue/purple/pink/orange)を保ったまま「淡い背景+彩度のある文字色」というライト版の役割を「沈んだ背景+浮き上がる文字色」に再設計している(詳細は`src/styles/tokens.css`のコメント参照)。`--color-orange-600`はライトでは「文字色専用に濃くした値」だが、ダークでは逆に「明るくした値」になり、階調が担う調整方向がモードによって反転する点に注意。

!NOTE: `components/dept/DeptCard.tsx`が描画する`Department.color`(`backend/.../ojt_seed.py`由来の生hex値)はCSS変数ではないためダークモードに自動追従しない。`lib/deptColor.ts`の`toneForDeptColor()`でアクセント色相(`Tone`)へ逆引きし、`theme.palette.accent[tone]`経由で描画することで対応している。バックエンドが未知の色を返した場合はニュートラル配色にフォールバックする。

!NOTE: 削除確認は`window.confirm`ではなくアプリ内`Dialog`(`ConfirmDialog`)を使う。ブラウザネイティブの確認ダイアログはスタイル・フォーカス制御をアプリ側から制御できないため。画面ごとの詳細な挙動は各画面仕様書(`docs/screens/*.md`)を参照。

!NOTE: `Mascot`コンポーネントは、Claude Designの`Mascot.dc.html`（div + 絶対配置のみで構成された素朴なキャラクター）をそのままReactに移植した。SVGやLottieを使わずCSSで完結させているため依存が増えず、`mood`("cheer"|"happy")と`color`(体色)の2パラメータだけで見た目を制御できる。

## パステルUIの共通設計

2026-09-28の改善仕様は [ui-refresh.md](ui-refresh.md) を参照。React + MUIを継続し、`tokens.css`の背景・文字・境界線・影・ページ余白を`theme.ts`と共通コンポーネントへ適用する。`palette.primary`/`secondary`もMUIが色演算するため、背景・文字と同様にCSS変数の実値を同期する。

- パステルの色相とマスコットを継承し、文字色と操作の優先順位を調整する。ボタン、フォーム、ダイアログ、表、タブはMUIテーマで統一する。
- `PageContainer`はコンテンツ幅を最大1440pxとし、ページ余白は`--page-gutter`（16〜40px）を使う。下部ナビが表示される幅ではその高さと`safe-area-inset-bottom`分の余白を確保する。
- `TopNav`は半透明のstickyヘッダー。1200px以上はアイコン付きの上部リンク、未満はDrawerを使う。600px未満ではホーム・日報・課題・資格勉強・その他の下部ナビも表示する。「その他」は同じDrawerを開く。Drawerは1200px以上へ広げると閉じる。
- 現在地は`aria-current="page"`と背景色で表し、課題詳細・学習チャットなどでも親項目を選択表示する。管理者用リンクのロール判定と本人のストリークを維持する。
- キーボード操作には本文へのスキップリンクとフォーカスリングを用意する。主なボタンは44px以上、モバイル入力文字は16px以上とし、動きを減らす設定では装飾の移動・アニメーションを抑える。

!NOTE: 下部ナビと上部Drawerのリンクは同じ定義から構成する。画面遷移をパネル切替と誤認させないよう、ナビ項目はReact RouterのLinkを使い、Tabsとして扱わない。

## レイアウト・レスポンシブ方針

`src/theme.ts`で定義済みのMUI標準`breakpoints`(`xs:0, sm:600, md:900, lg:1200, xl:1536`)をそのまま採用し、**`md`(900px)未満を「コンパクト表示」に切り替える原則の閾値**としてアプリ全体で統一している(例外はReport・課題一覧(`/assignments`)のヘッダー行と`TopNav`右側のユーザー表示で、いずれも`sm`を境界にする)。OJT三ペイン(`/ojt/panel`)・Quiz(`/study`)・StudyChat(`/study/chat`)の固定幅サイドバー/ペインは、`components/layout/CollapsibleAside.tsx`により`md`未満でMUI`Drawer`のオーバーレイ表示(ドロワー化)に切り替わり、`TopNav`のナビゲーションは管理者向け項目を含むため`lg`未満でハンバーガーメニュー+Drawerに切り替わる。Home(`/home`)は強み・ふり返り・ショートカット・学習度を全幅で縦に並べ、ショートカット3枚と、ふり返り・学習度の本文とボタンを`md`未満で縦積みにする。Report(`/report`)のKPT3カラムも`md`、ヘッダーボタン行のみ`sm`を境に縦積みへ変わる。`TopNav`右側のユーザー表示(表示名・ロール・アバター)も例外的に`sm`未満で隠し、ログアウトボタンが画面内に収まるようにしている(対象とする最小幅は320px。`sm`未満でロゴ文字も省略)。

!NOTE: 境界を原則`md`に統一した理由は、OJT三ペインの固定幅(左230px+右382px=612px)だけで`sm`(600px)を超えてしまい、`sm`を境界にするとタブレット縦持ち幅(768px前後)でも中央チャットが極端に狭くなるため。画面ごとに閾値がバラバラだと挙動を覚えにくくなる点も踏まえ、`md`をアプリ全体の判断基準としている。例外(Report・課題一覧のヘッダー行、`TopNav`右側のユーザー表示)は、レイアウト全体の切替ではなく、`sm`未満の狭い画面で個別の要素を画面内に収めるための調整に限っている。

!NOTE: 補助ペインの畳み方は「1カラム化(常時表示・縦積み)」ではなく「ドロワー化(オーバーレイ+開閉操作)」を採用した。固定幅サイドバーが持つ情報量(分野フィルタ・参照ナレッジ等)を維持しつつ、狭い画面では本文(チャット・設問)を優先して全幅表示できるため。

`CollapsibleAside`はMUIの`Drawer`(`variant="temporary"`)をポータル経由で描画するため、親の`display:flex`コンテナに置いても幅を消費しない。そのため各画面の外枠(flex比率・固定高さ)自体は変更せず、既存の`<aside>`を`<CollapsibleAside>`に置き換えるだけで対応している。`md`以上に戻った際は内部で開閉状態を自動的にリセットする(モバイル幅でドロワーを開いたまま画面を広げ、再度狭めたときに意図せず開いた状態にならないようにするため)。

!NOTE: `CollapsibleAside`は静的`<aside>`とDrawerとでJSXツリーの構造自体(`Box` vs `Drawer`)を切り替えるため、`md`境界をまたぐたびに`children`のサブツリーが再マウントされる。現状の`children`(課カード一覧・分野リスト等)はローカルUI状態を持たないため実害は無いが、将来的に検索フィルタ入力等のローカル状態を子要素へ追加する場合は、この再マウントで状態が消える点に注意が必要。

## バックエンドAPI設計の要点

- クイズは本人の解答履歴と復習予定から次の問題を選ぶ。「今の出題」をサーバーへ固定せず、解答POSTのquestionIdを元に採点・履歴・復習予定・達成率を保存するため、複数タブでも対象問題を取り違えない。
- 正解・解説はクイズ出題時のレスポンスに含めない（`QuizQuestion`スキーマ）。解答後にのみ`QuizAnswerResponse`で開示する。

!TIP: これにより、ブラウザの開発者ツールでネットワークタブを見ても事前に正解が漏れない、という実運用に近い挙動になる。

## ディレクトリ構成

詳細は各画面の仕様書（`docs/screens/*.md`）とAPI仕様書（`docs/api.md`）を参照。

## 2026-09-28の運用基盤拡張

追加モデルは `extension_models.py` に集約する。既存DBに破壊的な列変更をせず、`account_states`・`department_history`・`login_attempts`・`user_progress_categories`・`quiz_successes`・`ojt_threads/messages`・`agent_jobs`・`strength_candidates/evaluations`・`proposal_revisions/automation`・`submission_scores`を作成する。既存ユーザーの状態と共有進捗は起動時に欠けた行だけ移行し、変更済み行は上書きしない。アイコン補正と独自画像問題追加も既存DBへ適用する。この拡張のためにDBを削除する必要はない。

強み解析は永続ジョブで管理する。既定のmanualモードはCodexセッション連携、明示設定したopenaiモードはアプリ内の非同期ワーカーから外部APIを使う。`data/agent_jobs.py`がスナップショットとハッシュによる重複防止、`routers/development.py`が検証・状態更新・講師承認を担う。課題再生成は `routers/proposal_agent.py` で旧版との整合性を確認する。読み込み中の画面切替による古い応答の混入を `useResource`・`useOjt`・`useQuiz` で防ぐ。

実日報の強み解析入力は `schemas/strength_materials.py` の `StrengthAnalysisMaterials` を正本とし、`services/strength_materials.py` で旧形式の変換と検証を行う。新規ジョブは版付きの材料を保存してハッシュ化し、詳細・評価材料の取得と結果取込でも検証する。原文を変えずに出典と役割を固定し、日報の保存用スキーマから解析用の入力契約を分離する。旧ジョブは保存済みスナップショットから変換するため、DB移行・再シードは不要。詳細は [強み解析入力の仕様](strength-analysis-input.md) を参照。

能力・性格傾向の解釈は `strength_interpretations` に候補IDを主キーとして追加保存する。`kind,summary,scope_note` を既存候補と対応させ、追加行のない旧候補は能力・空の解釈として扱う。承認済み候補の置換は種類とスキルの組で行う。!NOTE: 列の破壊的変更や再シードを避け、既存DBと承認履歴を保持するための追加テーブルである。[能力・性格傾向の仕様](strength-profile.md)を参照。

> [!NOTE]
> 人間評価は運用で収集するデータであり、エージェント出力を人間ラベルとして埋めてはならない。実データ・2名の評価がない状態は「評価データ不足」のまま表示する。

## 部署別OJT設定の共通基盤

OJTの共通処理（本人×部署の会話保存、講師への明示相談と返信）と部署設定を分離する。
`data/ojt_configuration.py` が設定の取得・作成・一括更新、`schemas/ojt.py` が入力契約を担う。
既存の `departments`・`department_messages`・`knowledge_items` に加え、
`extension_models.OjtConfiguration`（`ojt_configurations`）に `quick_asks`・`reply_guidance`・`revision` を保存する。
`initialize_extensions` から不足する部署設定だけを初期化するため、既存DBの削除や既存行の列追加は不要。

設定更新は更新番号を条件にした原子的UPDATEで競合を検知し、部署情報・初期案内・ナレッジを同一トランザクションで保存する。
利用者の会話・講師の返信・配属履歴は独立したテーブルのまま維持する。ナレッジ件数は実際の登録数から取得する。
回答生成は `services/grounded_ojt.py` が選択部署の資料を語句検索し、本人の直近12発言と補足案内から引用付き回答を作る。共通の `services/llm.py` を使い、manualでは資料抜粋を返す。

フロントエンドでは両相談画面が `useOjt` の部署別質問候補を共有する。`OjtSettingsPage` と `useOjtConfiguration` が管理画面を提供し、
部署切替・アンマウント後の古い応答と二重保存を防ぐ。講師用ナビに「OJT設定」を追加し、既存のDrawerとモバイル導線を利用する。
保存済みの設定はOJT画面を開き直して反映する。一般利用者は管理画面・管理APIを利用できない。
部署名・資料・質問候補は空白のない長文も折り返し、設定フォームは親幅を上限とする。
共通の質問候補コンポーネントは高さ160px以内でスクロールし、長文の候補で会話欄が押し出されるのを防ぐ。

> [!NOTE]
> 現段階ではすべての講師が全部署を管理する。部署配属を管理権限として流用しない。
> 初期案内は現在の設定で表示し、過去の会話内容は設定変更時にも書き換えない。

適合性・カスタマイズ範囲・将来の拡張は [部署別OJTフレームワーク](ojt-framework.md) を参照。

## デモアカウントを作らない起動

運用環境では `CALIBOO_DEMO_SEED=false` を設定し、`python3 -m caliboo_api.manage --login-id admin --display-name 管理者` で初期管理者を対話作成する。パスワードは引数やファイルへ保存しない。この設定では課マスタ・問題マスタのみを投入し、公開済みの開発用ユーザー・日報・課題提出は作成しない。既存DBの開発アカウントは自動削除しないため、管理画面から無効化する。

## 個別行動と画面の自動更新（2026-09-28追加）

`learning_actions`を追加し、ユーザー、任意の承認済み強み、行動と達成の目安、期限、状態、振り返り、更新番号を保存する。選択時の強みをJSONで保存するため、後続の解析が本人の計画を変えない。既存DBは`create_all`でテーブルを追加し、既存データの変更・削除を必要としない。

ホームと強み画面の定期取得は`useAutoRefresh`と`useResource`が担う。表示中のみ5秒間隔で実行し、取得処理中・保存中には重ねず、非表示時に停止する。画面復帰時に取得し、対象変更・アンマウント後の古い応答を破棄する。フォームの下書きは取得結果から独立し、更新番号不一致をサーバー側の条件付きUPDATEで拒否する。

詳細は [個別学習仕様](personalized-learning.md) を参照。
## 外部生成provider（2026-09-29）

`services/llm.py`は明示設定した場合だけResponses APIへ接続する共通境界。モデルの型・引用は`services/assignment_proposal/llm_provider.py`が検証し、既存pipelineがproviderを切り替える。DBに認証情報を保存しない。`assignment_proposal_data`は確認待ちを原子的な条件付きINSERTで作り、長い推論中の同時依頼による重複を防ぐ。既存データの移行は不要。詳細は [生成AI provider仕様](ai-provider.md) を参照。


## 生成AIの自動ジョブ処理（2026-09-29）

`agent_job_contexts`に課題進捗のスナップショット、`agent_job_executions`に試行回数・期限付き取得権・再試行時刻・エラーコードを保存する。既存DBへテーブルを追加し、既存の材料形式と手動取込を維持する。強みの進捗は重複判定に含め、達成の引用材料とは分離する。

`main.lifespan`が明示設定時だけ`services/ai_worker.py`を起動し、停止時は進行中の処理を待つ。`data/job_execution.py`が条件付きUPDATEで取得権を確保し、`services/job_inference.py`は取得済みスナップショットだけをモデルへ渡す。推論中はDBトランザクションを開かず、保存直前の取得権とジョブ状態を同じトランザクション内で検証する。期限切れ・別処理済み・対象無効化の結果は公開しない。

詳細な状態、タイミング、運用手順は [生成AIワーカー](ai-worker.md) を参照。


## OJT回答の根拠と保存境界

既存の`OjtMessage.references`のJSONへ資料名・取得時点のID・原文引用を保存するため、DBの列変更は不要。生成前に本人の同部署の会話と資料・設定版を収集し、トランザクションを閉じる。生成後は設定版を条件にしたUPDATEで書込みを開始し、対象の有効状態を確認して質問と回答を同時保存する。資料更新中の結果は409として再送を促す。

`ChatBubble`は引用をblockquoteの平文として表示し、資料名だけの旧履歴も扱う。原文のHTMLは実行せず、長い引用は既存の可変幅と折り返しを使う。仕様と検索の限界は [OJT回答仕様](grounded-ojt.md) を参照。


## 学習チャットの文脈と失敗時の保持

`StudyChatRequest`が公開問題と最大12発言を型検証し、`services/chat_reply.py`が共通LLM境界で学習回答を生成する。採点データと永続的な他人の会話は取得しない。180KBを超える会話は古い発言を除いて送信し、現在の質問・公開問題は原文を維持する。新しいDBテーブルは不要。

`useStudyChat`が成功した会話、現在の入力、問題の文脈、失敗した要求を分けて保持する。初期問題だけ先に表示して回答を自動取得し、以後は成功した質問・回答をまとめて追加する。refで二重送信とStrictModeでの重複開始を防ぎ、離脱後の応答を無視する。画面には待ち状態・失敗・再送を表示する。詳細は [学習チャット仕様](contextual-study-chat.md) を参照。


## 個人別のクイズ復習

`quiz_attempts`へユーザー・問題・選択肢・正誤・解答時刻、`quiz_reviews`へユーザー×問題の累積回数・連続正解・直近の正誤/時刻・復習時刻を保存する。時刻はUTCのUnix秒。追加テーブルのみで既存DBへ適用し、過去の日時や履歴を合成して移行しない。既存QuizSuccessと個人進捗は保持する。

`data/quiz_review.py`が間隔と候補の優先順位を管理する。累積回数と連続正解はupsertのSQL式で更新し、同時解答の取りこぼしを防ぐ。採点・履歴・予定・達成率は1トランザクションで保存する。正解済み件数は既存の一意キーを継続する。詳細は [復習仕様](quiz-review.md) を参照。


## 実日報ホールドアウト評価の分離

`routers/holdout.py`と`strength_holdout_cases/labels`で、提出日報の凍結→別アカウント2名の独立ラベル→結果→受容性を永続化する。原文、材料版とハッシュ、評価者・日時、変更できないラベルと結果を保持し、同時書込はケースのロックと複合主キーで順序を保つ。通常解析とは`services/strength_result.py`の引用検証だけを共有し、評価結果からStrengthCandidateを作らない。

旧`strength_evaluations`は参考として保持し、新方式への自動移行や合格集計をしない。最新ケースのprovider/model/promptVersionを集計条件とし、別版の結果を合算しない。実データの由来と画面外の未閲覧は責任者の確認が必要。[手順と限界](strength-holdout.md)を参照。
