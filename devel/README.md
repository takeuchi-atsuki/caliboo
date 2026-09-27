# 開発用スクリプト

Calibooの配布zip作成・セットアップ・開発サーバー起動に使うスクリプト群。

| スクリプト | 用途 |
| --- | --- |
| `build.sh` | ソースコード一式を`release/YYYYMMDD_Caliboo.zip`へまとめる(送る側で実行) |
| `setup.sh` | 展開後に、Pythonパッケージとnpmパッケージをインストールする(受け取る側で実行) |
| `dev-server.sh` | バックエンド(`:8000`)とフロントエンド(`:5173`)の開発サーバーをまとめて起動する |

## 配布zipの作成(送る側)

前提: `rsync`・`zip`コマンド

1. `package.json`の依存を変更した場合は、`frontend/`で`npm install`を実行して`package-lock.json`を更新しておく
2. `bash ./devel/build.sh`を実行する
3. 作成された`release/YYYYMMDD_Caliboo.zip`を送り、受け取る側にはこのファイル(`devel/README.md`)の手順に従うよう伝える

同梱するのは`backend/`・`frontend/`・`docs/`・`devel/`・`.devcontainer/`・`.claude/`・`BACKLOG.md`。同じ日に再実行するとzipは上書きされる。作業用の`devel/.temp/`は残るが、次回実行時に作り直される。

> [!NOTE]
> 主に次のものは同梱しない(除外の全リストは`build.sh`の`cpdir`を参照)。
>
> - `node_modules/`・`backend/.venv/`・`dist/`・`coverage/`: 容量が大きく、展開先で`setup.sh`により再生成できるため
> - `backend/var/`(SQLiteのDB): 起動時に`backend/var/caliboo.db`として自動作成される。送る側のデータは引き継がない
> - `.claude/settings.local.json`: 個人の権限設定のため

## 別の環境でのセットアップ(受け取る側)

以下の2通りのどちらかで動かす。

> [!WARNING]
> Windowsでは、zipをWSLのホーム配下(例: `~/Caliboo`)へ`unzip`で展開すること。Windows側のフォルダ(`C:\`、WSLから見た`/mnt/c`)に置くと、`npm ci`・`pip install`が極端に遅くなる。またファイル変更の通知が届かず、ViteのHMRやuvicornの自動リロードが効かないことがある。
>
> 受け取った側でgit管理する場合、`core.autocrlf=true`だと`.sh`の改行がCRLFになり、`$'\r': command not found`で失敗する。`.sh`はLFのまま扱うこと。

### A. Dev Container で動かす

前提: Docker、VSCode拡張機能「Dev Containers」(WindowsではWSL上のフォルダを開くため拡張機能「WSL」も)

1. 展開した`Caliboo`フォルダをVSCodeで開く(WSLではそのフォルダで`code .`を実行する)
2. コマンドパレットで「Dev Containers: Reopen in Container」を実行する
3. コンテナ作成時に依存のインストール(`devel/setup.sh`)が自動で走るので、ターミナルに`setup complete!`が出るまで待つ
4. VSCodeのターミナルで`bash ./devel/dev-server.sh`を実行する

> [!NOTE]
> Dev Containerの設定は所内ネットワーク向けの項目を含むが、所外でもビルドできるようにしてある。
>
> - 内部CA証明書は、取得できなければ警告を出して飛ばす
> - 所内DNSの固定指定(`devcontainer.json`の`--dns`)は既定でコメントアウトしている

### B. ホスト(WSL / Linux / macOS)で直接動かす

前提: Python 3.12以降、Node.js 22.4以降。Windowsの場合はWSL上で実行する。Debian/Ubuntu(WSLの既定)では、`sudo apt install python3-venv`でvenvの作成機能も入れておく。

1. 展開した`Caliboo`フォルダで`bash ./devel/setup.sh`を実行し、`setup complete!`が出るまで待つ
2. `bash ./devel/dev-server.sh`を実行する(Ctrl+Cで停止)
3. VSCodeで`Caliboo`フォルダを開き、Pythonインタープリタに`backend/.venv/bin/python`を選択する

`python3`が3.12未満の場合は、`PYTHON=python3.12 bash ./devel/setup.sh`のようにPythonを指定する。

> [!NOTE]
> ホストでは依存を`backend/.venv`へインストールする。システムのPythonを汚さないためと、PEP 668によりシステムPythonへの`pip install`が拒否される環境が多いため。

テスト・静的解析(`docs/api.md`「動作確認方法」)や`.claude/skills/`の手順は、素の`python3`を前提にしている。ホストで開発するときは、ターミナルで`source backend/.venv/bin/activate`を実行してから使う。

### 動作確認

1. ブラウザで`http://localhost:5173/`を開き、ログイン画面が表示されることを確認する
2. 開発用アカウント(例: ログインID`yuki`・パスワード`caliboo-yuki`、一覧は`docs/screens/login.md`「開発用アカウント」)でログインし、ホーム画面が表示されることを確認する

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
