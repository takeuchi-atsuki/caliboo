# 開発用スクリプト

Calibooの配布zip作成・セットアップ・開発サーバー起動に使うスクリプト群。

| スクリプト | 用途 |
| --- | --- |
| `build.sh` | ソースコード一式を`release/YYYYMMDD_Caliboo.zip`へまとめる(送る側で実行) |
| `setup.sh` | 展開後に、Pythonパッケージとnpmパッケージをインストールする(受け取る側で実行) |
| `dev-server.sh` | バックエンド(`:8000`)とフロントエンド(`:5173`)の開発サーバーをまとめて起動する |

## 配布zipの作成(送る側)

前提: Bash、Python 3.12以降。Pythonの標準ライブラリで作成するため、`rsync`・`zip`は不要。

1. `package.json`の依存を変更した場合は、`frontend/`で`npm install`を実行して`package-lock.json`を更新しておく
2. WSL / Linux / macOSでは`bash ./devel/build.sh`、Windows Git Bashでは`bash ./devel/windows/build-windows.sh`を実行する
3. 終了コードが0で`complete!`が出たことを確認する
4. 作成された`release/YYYYMMDD_Caliboo.zip`を送り、受け取る側にはZIP直下の`Caliboo/README.md`の手順を案内する

ZIPは`Caliboo/`をルートとする。README・CHANGELOG、アプリのソースコードと依存定義、セットアップ・起動スクリプトを同梱する。設計資料・Dev Container設定・バックログは存在する場合に同梱する。開発者向けの資料のうち、配布対象外の作業記録やAI設定を参照するリンクはリポジトリで確認する。

> [!NOTE]
> 配布対象は`package_release.py`に定義する。アプリの起動に必要なファイルを追加した場合は同梱対象も確認する。以下は同梱しない。
>
> - 元のDB（`backend/var/`、その他のSQLiteファイル）・環境ファイル・秘密設定・個人のSSH設定
> - 依存パッケージ・ビルド生成物・テストキャッシュ・作業用ファイル
> - 開発専用のテスト（`backend/tests/`、フロントエンドのテストファイルと`frontend/src/test/`、配布処理の回帰テスト）
> - 開発AI設定（`.claude/`・`.codex/`等）・`devel/poc_takeuchi/`の実行記録・個人別PoC報告
>
> 途中で入力不足・圧縮・検証等のエラーが発生した場合は非ゼロで終了する。同日の正常なZIPは、新規ZIPの読み戻し検証が成功した場合にのみ置き換える。作成途中の一時ZIPは通常のエラー終了時に削除する。

## 完全チェックアウトでの開発検証（送る側）

以下は開発支援設定を含む完全なGitチェックアウト上で実行する。アプリケーションの単体・統合テストには配布対象外の`.codex/`を参照するものがあるため、配布ZIPには開発専用テスト一式を含めない。

配布スクリプトの回帰テストは完全チェックアウトのルートから実行する。

```bash
python3 -m unittest discover -s devel -p 'test_package_release.py' -v
```

アプリケーションのテスト・静的解析・カバレッジは[READMEの完全チェックアウト向け手順](../README.md#開発検証コマンド完全チェックアウトのみ)を参照する。

## 別の環境でのセットアップ(受け取る側)

以下のいずれかの方法で動かす。まずZIPを空のフォルダに展開し、`Caliboo/`へ移動する。

> [!WARNING]
> WindowsでWSLを使う場合は、zipをWSLのホーム配下(例: `~/Caliboo`)へ`unzip`で展開すること。Windows側のフォルダ(`C:\`、WSLから見た`/mnt/c`)に置くと、`npm ci`・`pip install`が極端に遅くなる。またファイル変更の通知が届かず、ViteのHMRやuvicornの自動リロードが効かないことがある。
>
> 受け取った側でgit管理する場合、`core.autocrlf=true`だと`.sh`の改行がCRLFになり、`$'\r': command not found`で失敗する。`.sh`はLFのまま扱うこと。

### A. Dev Container で動かす

前提: Docker、VSCode拡張機能「Dev Containers」(WindowsではWSL上のフォルダを開くため拡張機能「WSL」も)

1. 展開した`Caliboo`フォルダをVSCodeで開く(WSLではそのフォルダで`code .`を実行する)
2. コマンドパレットで「Dev Containers: Reopen in Container」を実行する
3. コンテナ作成時に依存のインストール(`devel/setup.sh`)が自動で走るので、ターミナルに`setup complete!`が出るまで待つ
4. VSCodeのターミナルで初回の[ローカルアカウント設定](#初回起動前のローカルアカウント設定)を行い、`CALIBOO_DEMO_SEED=false CALIBOO_AI_PROVIDER=manual bash ./devel/dev-server.sh`を実行する

> [!NOTE]
> 配布ZIPに開発者個人のSSH設定は含まれない。GitHubへのSSH接続設定はローカルPoCの起動には不要。

### B. ホスト(WSL / Linux / macOS)で直接動かす

前提: Python 3.12以降、Node.js 22.4以降。WindowsでWSLを使う場合はWSL上で実行する。Debian/Ubuntu(WSLの既定)では、`sudo apt install python3-venv`でvenvの作成機能も入れておく。

1. 展開した`Caliboo`フォルダで`bash ./devel/setup.sh --venv`を実行し、`setup complete!`が出るまで待つ
2. 初回の[ローカルアカウント設定](#初回起動前のローカルアカウント設定)を行う
3. `CALIBOO_DEMO_SEED=false CALIBOO_AI_PROVIDER=manual bash ./devel/dev-server.sh`を実行する(Ctrl+Cで停止)
4. VSCodeで`Caliboo`フォルダを開き、Pythonインタープリタに`backend/.venv/bin/python`を選択する

`python3`が3.12未満の場合は、`PYTHON=python3.12 bash ./devel/setup.sh --venv`のようにPythonを指定する。

> [!NOTE]
> ホストでは依存を`backend/.venv`へインストールする。システムのPythonを汚さないためと、PEP 668によりシステムPythonへの`pip install`が拒否される環境が多いため。

完全チェックアウトでテスト・静的解析を行う場合は、ターミナルで`source backend/.venv/bin/activate`を実行してから使う。

### C. Windows Git Bashで直接動かす

前提: Windows版Python 3.12以降、Windows版Node.js 22.4以降、Git Bash。WSLのPython/NodeではなくWindows版を利用する。

1. ZIPを展開し、Git Bashで`Caliboo/`へ移動する
2. `bash ./devel/windows/setup-windows.sh`を実行する
3. 初回の[ローカルアカウント設定](#初回起動前のローカルアカウント設定)を行う
4. `CALIBOO_DEMO_SEED=false CALIBOO_AI_PROVIDER=manual bash ./devel/windows/dev-server-windows.sh`を実行する（Ctrl+Cで停止）
5. ブラウザで`http://localhost:5173/`を開く

### 初回起動前のローカルアカウント設定

新規展開先では、セットアップ完了後、最初のサーバー起動より前にローカルPoC専用の管理者を作成する。既定の開発アカウントを投入しないようにし、ID・表示名は利用者が決める。パスワードはコマンドの引数やファイルに記載せず、管理者作成コマンドの対話入力で設定する。

WSL / Linux / macOSのホストの場合:

```bash
read -r -p '管理者のログインID: ' local_admin_id
read -r -p '管理者の表示名: ' local_admin_name
CALIBOO_DEMO_SEED=false backend/.venv/bin/python -m caliboo_api.manage \
  --login-id "$local_admin_id" --display-name "$local_admin_name"
```

Dev Containerでは上の`backend/.venv/bin/python`を`python3`に、Windows Git Bashでは`backend/.venv/Scripts/python.exe`に置き換える。この設定は初回のみ行い、起動・再起動時は`CALIBOO_DEMO_SEED=false`を指定する。詳細は[既定のデモアカウントを投入しない起動方法](../docs/architecture.md#デモアカウントを作らない起動)を参照する。

### 動作確認（配布ZIP）

1. ブラウザで`http://localhost:5173/`を開き、ログイン画面が表示されることを確認する
2. 自分で作成した管理者でログインし、講師のユーザー管理画面から架空の新入社員アカウントを作成する。ログアウトして、その合成アカウントでログインし、ホーム画面が表示されることを確認する
3. 日報画面で合成データ（例: Keep「架空の研修で資料を読んだ」、Problem「架空の手順を確認中」、Try「明日は架空の演習を復習する」）を入力して提出する
4. サーバーを停止して同じ展開先から`CALIBOO_DEMO_SEED=false CALIBOO_AI_PROVIDER=manual`を指定して再起動し、再ログイン後の日報履歴に提出内容が表示されることを確認する
5. サーバー停止後、必要に応じて`(cd frontend && npm run build)`を実行し、ビルドできることを確認する

> [!TIP]
> ローカルPoCでは実際の日報や秘密情報を入力しない。外部AIを使わないよう`CALIBOO_AI_PROVIDER`を未設定または`manual`にし、`CALIBOO_SQLITE_PATH`も未設定の状態で起動する。新しいSQLite DBが展開先の`backend/var/`に作られる。依存導入にはネットワーク接続が必要な場合がある。

Dev Containerでブラウザから開けない場合は、VSCodeの「ポート」タブで`5173`が転送されているか確認する。

## setup.sh のオプション

| 指定 | 動作 |
| --- | --- |
| なし | 自動判定。コンテナ内(`/.dockerenv`がある、または`REMOTE_CONTAINERS=true`)なら`--system`、それ以外なら`--venv` |
| `--venv` | `backend/.venv`を作成してインストール |
| `--system` | 現在の`python3`(`PYTHON`指定時はそのPython)へ直接インストール。rootでない場合は、pipによりユーザー領域(`~/.local`)へ入る |
| `--help` | 使い方を表示 |
| 環境変数`PYTHON` | 使うPythonコマンドを指定(既定: `python3`) |

`PYTHON`を指定してセットアップした場合は、`dev-server.sh`の起動時にも同じ`PYTHON`を指定する。`dev-server.sh`は`PYTHON`→`backend/.venv`→`python3`の順に、バックエンドをimportできるPythonを探す。

> [!TIP]
> フロントエンドは`npm install`ではなく`npm ci`で、`package-lock.json`どおりの版を入れる。配布先で依存の版がずれて挙動が変わるのを防ぐため。バックエンドは`pyproject.toml`の下限指定(`>=`)のみで版を固定していないため、配布先では新しい版が入りうる。

## トラブルシュート

| 症状 | 対処 |
| --- | --- |
| `setup.sh`が「Python 3.12 以降が必要です」「Node.js 22.4 以降が必要です」で止まる | 該当バージョンをインストールする。Pythonは`PYTHON=python3.12`のように指定もできる |
| `setup.sh`が「venv を作成できませんでした」で止まる | `sudo apt install python3-venv`(または`python3.12-venv`)を実行し、`setup.sh`を再実行する |
| `npm ci`が`package-lock.json`との不一致で失敗する | 送る側で`npm install`を実行し、`package-lock.json`を更新したzipを作り直してもらう |
| `dev-server.sh`が「バックエンドを起動できるPythonが見つかりません」「フロントエンドの依存が未インストールです」で止まる | `bash ./devel/setup.sh`を実行する(`PYTHON`を指定した場合は起動時も同じ指定をする) |
| Dev Containerの作成時にセットアップが失敗した | 原因を解消し、コンテナ内のターミナルで`bash ./devel/setup.sh`を再実行する |
| 所内でDev Containerから名前解決できない | `devcontainer.json`の`--dns`2行のコメントを外し、「Dev Containers: Rebuild Container」を実行する |
| 所内で内部CAが必要な接続(社内Git等)が証明書エラーになる | 一時的に内部CAを取得できなかった結果がDockerのキャッシュに残っている。「Dev Containers: Rebuild Without Cache and Reopen in Container」で作り直す |
