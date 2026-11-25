# Caliboo

Calibooは、新人研修向けのパーソナライズ学習支援アプリです。日報による振り返り、OJTでの相談、資格勉強、課題演習を通じて、新入社員の学習と講師の育成支援をつなぎます。

現在は、画面・業務フローの検証と強み解析のPoCを進めている開発段階です。ReactのフロントエンドとFastAPIのバックエンドで構成し、学習記録などをSQLiteに保存します。

## 主な機能

| 機能 | 内容 |
| --- | --- |
| ホーム | 学習の進捗、日報への導線、承認済みの強みを表示 |
| 日報 | Keep / Problem / Tryときもちを記録し、下書き・提出履歴を管理 |
| OJT相談 | 部署ごとのチャット、相談履歴、講師への相談依頼と返信。講師が部署・案内・質問候補・ナレッジを設定 |
| 資格勉強 | 分野別のクイズ、正誤判定・解説、学習サポートチャット |
| 課題演習 | 講師による課題作成・配信、新入社員の回答提出、講師のフィードバック、ブラウザ内JavaScriptワークスペース |
| 強み・育成支援 | 日報や課題を材料とした解析ジョブ、強み候補の講師承認、根拠・育成アクションの表示 |
| 次の一歩 | 強みのヒントから本人が行動・達成の目安・期限を決め、実践と振り返りを記録。強みと配信課題は表示中に5秒ごとに更新 |
| 強み解析PoC | デモシナリオや外部から取り込んだ実行結果による解析・レビューの検証 |
| ユーザー管理 | 講師によるアカウント・配属の管理、本人のパスワード変更、管理者発行コードによる再設定 |

新入社員は`member`、講師は`admin`のロールで利用します。

> [!NOTE]
> OJTは部署資料の検索と原文引用に対応しています。既定は資料の抜粋、openai設定時は文脈に沿った回答を生成します（[仕様](docs/grounded-ojt.md)）。学習チャットは公開問題と直近の会話を使います（[仕様](docs/contextual-study-chat.md)）。生成解説はopenai設定時に利用できます。既定の手動モードはCodexセッションの結果を取り込む方式で、外部LLM APIキーは不要です。`CALIBOO_AI_PROVIDER=openai`とモデル・キーを起動環境に設定すると、強み解析と個人別課題案・再生成を自動処理します。本人への公開は講師承認後です。[設定](docs/ai-provider.md)・[自動処理と復旧](docs/ai-worker.md)を参照してください。詳しくは[追加機能の実装仕様](docs/backlog-implementation.md)を参照してください。

初回の個人別課題案には、明示設定でOpenAI Responses APIを利用できます。材料の引用を検証し、講師の確認後に配信します。設定・送信材料・失敗時の再試行は [生成AI provider仕様](docs/ai-provider.md) を参照してください。

## 技術構成

| 領域 | 使用技術 |
| --- | --- |
| フロントエンド | React 18 / TypeScript / Vite / MUI / React Router |
| バックエンド | Python 3.12以降 / FastAPI / SQLAlchemy |
| データベース | SQLite |
| 認証 | パスワード認証・HttpOnly Cookieによるセッション管理 |
| テスト・静的解析 | pytest / pytest-cov / flake8 / Vitest / Testing Library / TypeScript |
| 開発環境 | VS Code Dev Containers、またはWSL / Linux / macOS |

## セットアップと起動

以下のコマンドは、リポジトリのルートディレクトリで実行します。

### 配布ZIPから動かす

ZIPを空のフォルダに展開し、`Caliboo/`に移動して以下のセットアップと起動を実行してください。元のSQLite DB・秘密設定・作業記録は同梱されず、初回起動時に開発用のDBが新規作成されます。外部AI接続や実際の日報は不要です。

送る側の配布ZIP作成手順、Windows Git Bash用スクリプト、合成日報での再起動確認については[開発用スクリプト](devel/README.md)を参照してください。配布内容の変更履歴は[CHANGELOG.md](CHANGELOG.md)に記録します。

### ローカル環境で動かす

前提となるツールは次のとおりです。

- Python 3.12以降（`venv`を利用できること）
- Node.js 22.4以降とnpm
- Bash（WindowsではWSLを使用）

依存パッケージをインストールします。

```bash
bash ./devel/setup.sh --venv
```

初回は[ローカルアカウント設定](devel/README.md#初回起動前のローカルアカウント設定)で、利用者自身がローカルPoC専用の管理者と架空の新入社員を用意する手順を確認してください。管理者作成後に起動します。

```bash
CALIBOO_DEMO_SEED=false CALIBOO_AI_PROVIDER=manual bash ./devel/dev-server.sh
```

セットアップはPythonの仮想環境を`backend/.venv/`に作成し、バックエンドの開発用依存とフロントエンドの依存をインストールします。起動スクリプトは両方の開発サーバーを立ち上げます。停止は`Ctrl+C`です。

Pythonのコマンドを指定する場合は、セットアップ・起動の両方に同じ指定を付けます。

```bash
PYTHON=python3.12 bash ./devel/setup.sh --venv
CALIBOO_DEMO_SEED=false CALIBOO_AI_PROVIDER=manual PYTHON=python3.12 bash ./devel/dev-server.sh
```

> [!TIP]
> Windowsでは、リポジトリをWSLのLinuxファイルシステム上（例: `~/Caliboo`）に置いてください。`/mnt/c`配下では依存のインストールが遅くなったり、ファイル変更の検知が機能しなかったりすることがあります。

### Dev Containerで動かす

DockerとVS Codeの「Dev Containers」拡張機能を用意します。WindowsではWSL上のフォルダを開きます。

1. リポジトリをVS Codeで開きます。
2. コマンドパレットから「Dev Containers: Reopen in Container」を実行します。
3. コンテナ作成時の依存インストールが完了するまで待ちます。
4. 初回はコンテナ内で[ローカルアカウント設定](devel/README.md#初回起動前のローカルアカウント設定)の管理者作成を行い、次のコマンドで起動します。

```bash
CALIBOO_DEMO_SEED=false CALIBOO_AI_PROVIDER=manual bash ./devel/dev-server.sh
```

依存のインストールを再実行する場合は、コンテナ内で`bash ./devel/setup.sh`を実行してください。

### ブラウザで確認する

| 用途 | URL |
| --- | --- |
| アプリ | <http://localhost:5173/> |
| APIドキュメント（Swagger UI） | <http://localhost:8000/docs> |
| OpenAPI定義 | <http://localhost:8000/openapi.json> |

アプリを開き、[ローカルアカウント設定](devel/README.md#初回起動前のローカルアカウント設定)で作成したアカウントでログインします。講師のユーザー管理画面から合成の新入社員アカウントを作成し、そのアカウントで日報の動作を確認します。ログイン情報は利用者がローカルで決め、公開ドキュメントに記載しません。既定のデモアカウントを投入しない起動方法は[アーキテクチャの設定手順](docs/architecture.md#デモアカウントを作らない起動)を参照してください。

Dev Containerで画面を開けない場合は、VS Codeの「ポート」タブで`5173`の転送を確認してください。

## データ保存と設定

SQLiteのデータベースは初回起動時に自動作成され、以後の起動でも同じファイルを利用します。別途DBサーバーを起動する必要はありません。

| 環境変数 | 既定値 | 用途 |
| --- | --- | --- |
| `CALIBOO_SQLITE_PATH` | `backend/var/caliboo.db`（リポジトリからの絶対パス） | SQLiteファイルの保存先 |
| `CALIBOO_COOKIE_SECURE` | `false` | `true`または`1`でセッションCookieにSecure属性を付与 |

設定を変える場合は、起動するシェルで環境変数を指定します。通常のローカル開発は既定値のままで動作します。

> [!NOTE]
> 開発時はHTTPで利用するため、`CALIBOO_COOKIE_SECURE`は既定で無効です。また、フロントエンドからの`/api`リクエストはViteがバックエンドへ転送し、Cookie認証に必要な同一オリジンでの通信を保ちます。

## 開発・検証コマンド（完全チェックアウトのみ）

以下はGitリポジトリを完全にチェックアウトした開発者向けです。配布ZIPには開発専用のテストや`.codex/`を含めません。配布版の受け入れ確認は[セットアップ・起動・合成日報の手順](devel/README.md#動作確認配布zip)に従ってください。セットアップ後のフロントエンドビルド（`npm run build`）は配布版でも実行できます。

ローカル環境で`--venv`によるセットアップを行った場合は、検証前に仮想環境を有効にします。

```bash
source backend/.venv/bin/activate
```

### バックエンド

```bash
# 静的解析
(cd backend && python3 -m flake8 src tests)

# 単体テスト・カバレッジ
(cd backend && python3 -m pytest --disable-socket tests/unit/ --cov=caliboo_api --cov-report=term-missing)

# 統合テスト
(cd backend && python3 -m pytest --disable-socket tests/integration/)
```

### フロントエンド

```bash
# 型検査
(cd frontend && npm run lint)

# テスト・カバレッジ
(cd frontend && npm run test:coverage)

# ビルド
(cd frontend && npm run build)
```

カバレッジの基準は95%以上です。フロントエンドの計測対象・しきい値は[テスト設定](frontend/vite.config.ts)、変更時の確認手順は[開発ルール](AGENTS.md)を参照してください。画面操作の確認項目は[手動テストケース](docs/manual-test-cases.md)にまとめています。

## ディレクトリ構成

```text
backend/
  src/caliboo_api/   API・認証・データアクセス・解析処理
  tests/            単体テスト・統合テスト
  var/              SQLiteデータベース（起動時に生成）
frontend/
  src/              画面・共通コンポーネント・APIクライアント
docs/               設計・画面仕様・テスト資料
devel/              セットアップ・起動・配布用スクリプト
.devcontainer/      Dev Container設定
.codex/             開発支援用のルール・スキル・エージェント設定
AGENTS.md           開発ルール
BACKLOG.md          課題・対応状況
```

## 関連ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [アーキテクチャ](docs/architecture.md) | 全体構成、永続化、認証、技術選定 |
| [API仕様](docs/api.md) | エンドポイントと入出力 |
| [部署別OJTフレームワーク](docs/ojt-framework.md) | 適合性の判断、部署設定、管理画面、拡張範囲 |
| [画面仕様](docs/screens/) | ログイン・日報・OJT・資格勉強・課題・強み解析PoC |
| [追加機能の実装仕様](docs/backlog-implementation.md) | 強み承認、エージェントジョブ、ユーザー管理などの拡張 |
| [UI改善仕様](docs/ui-refresh.md) | 共通デザイン、ナビゲーション、レスポンシブ表示 |
| [総合テスト観点](docs/test-perspectives.md) | テストで確認する仕様と観点 |
| [手動テストケース](docs/manual-test-cases.md) | 画面・操作の確認手順 |
| [開発用スクリプト](devel/README.md) | セットアップの詳細、配布zip作成、トラブルシュート |
| [CI品質ゲート](docs/ci-quality-gates.md) | GitHub Actionsの起動範囲、検証候補、ローカル再現方法 |
| [バックログ](BACKLOG.md) | 未決事項と対応状況 |
| [開発ルール](AGENTS.md) | ファイル種別ごとの規約と完了前の確認 |

機能拡張やUI変更については、追加機能の実装仕様・UI改善仕様もあわせて参照してください。
