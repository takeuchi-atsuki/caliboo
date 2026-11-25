# 共有DBの構築・移行・検証（issue #25）

## 対象と構成

まずは1台、合成データのみ、2つの独立ブラウザセッションを対象とする。無料のPostgreSQL 18（OSS）とpsycopg 3、既存のSQLAlchemy/FastAPIを使用する。Windows/iOSを含むクライアントは同じFastAPIへブラウザで接続し、DBへ直接接続しない。外部LLMは使用せず、`CALIBOO_AI_PROVIDER=manual`に固定する。

!NOTE: SQLiteはローカル検証に向くが、PCごとのファイルを共有する構成では複数端末の記録を一元化できない。共有DBを明示選択にすることで既存のローカル実行・テストを壊さず導入を検証できる。

- `CALIBOO_DATABASE_URL`未設定：既存の`CALIBOO_SQLITE_PATH`、自動初期化、シード互換を維持する。
- `CALIBOO_DATABASE_URL`設定：`postgresql://`または`postgresql+psycopg://`形式を受け付け、psycopg 3を使う。不正・空文字・接続不能はエラー。SQLiteへのフォールバックはない。
- 共有モードのAPI起動はスキーマ検査のみ。管理CLIによる初期化または移行を先に行う。既定でデモユーザーを生成しない。
- テストは隔離ディレクトリ、ローカルループバックの別ポート（例：55425、APIは8255）、別の空DBを使用する。

## 新規DBの準備

PostgreSQL 18をローカルホストの専用クラスタに用意し、既存業務クラスタと分離する。テスト時はループバックのみで待ち受ける。空の専用DBとDB所有ロールを用意する（検証DB名は例として `caliboo_issue25_init`）。通常のアプリ実行ロールは必要なテーブル・シーケンスへのアクセス権だけを与える。DB接続先は起動するプロセスの環境に設定し、接続文字列やパスワードをソース、共有ログ、PR、コマンド履歴に記録しない。

```bash
# ローカルの安全な入力で CALIBOO_DATABASE_URL を設定してから実行
export CALIBOO_AI_PROVIDER=manual
cd backend
python -m caliboo_api.db_admin init
python -m caliboo_api.manage --login-id test-admin --display-name '合成管理者'
python -m uvicorn caliboo_api.main:app --host 127.0.0.1 --port 8255
```

`manage`はパスワードを対話入力で受け取り、APIと同じDBを参照する。初回初期化の`--demo`は既存のデモアカウント・合成シードを入れたい隔離DBに限って明示する。初期化先にテーブルが存在すれば拒否する。起動時に`CALIBOO_DEMO_SEED`の指定で共有モードのデモシードが追加されることはない。

## 単一SQLiteスナップショットからの移行

現行版で生成された40表のSQLiteを対象とし、複数のSQLiteや既存PGへのマージは行わない。新規初期化(`init`)と移行(`migrate`)は排他的な選択肢で、移行先は例えば`caliboo_issue25_migrate`という別のテーブルのないDBを用意する。実データでの実施は本issueの検証対象外。スナップショットにも認証ハッシュやセッション、業務データが含まれるため、合成データを使い、アクセスを制限する。

```bash
# SQLite側を停止してから、合成データのファイルを明示
python -m caliboo_api.db_admin snapshot --source /test/source.db --output /test/source.snapshot.db

# 空の移行先を CALIBOO_DATABASE_URL に設定（init は実行しない）
python -m caliboo_api.db_admin migrate --snapshot /test/source.snapshot.db
python -m caliboo_api.db_admin verify --snapshot /test/source.snapshot.db
```

処理内容：

1. SQLiteを読み取り専用で開き、バックアップAPIで新規スナップショットを作成する。既存ファイルへの上書きは行わない。
2. integrity_check、foreign_key_checkと現行版の全テーブル・列構成を検査する。
3. PGのトランザクション内でスキーマを作り、外部キー依存順で全行を移す。ID、文字列日時、日本語、JSON（SQL NULLとJSON nullの区別）、認証・権限、ジョブ状態を保つ。AUTOINCREMENTの既存上限とPK最大値からPG採番を設定する。
4. 全40表の件数・標準化した行内容のSHA-256・採番上限を照合する。成功のみコミットし、失敗時はDDLと行を巻き戻す。スナップショットは変更しない。
5. `verify`を独立に再実行して照合する。PGへのログインやデータ更新を始める前に行う。出力はテーブル数・合計行数のみ。

!NOTE: 入力に現在のDB制約違反（孤立外部キー、重複確認待ち課題案など）がある場合は自動修正・欠損・飛ばし処理をせず中断する。SQLite旧版の移行や業務レコードの補完は別途対応とする。

## バックアップ、復元、停止時の確認

検証用PGへの書込を止め、PostgreSQL 18付属の`pg_dump`でカスタム形式バックアップを取得する。接続先は`PGHOST`、`PGPORT`、`PGUSER`、`PGDATABASE`と対話入力などの安全な方法で設定する。機密値はコマンド引数に含めない。バックアップはアクセス制限されたディレクトリに新規作成する。

```bash
# PGDATABASE = 検証用移行DB（書込停止）、新規ファイルに出力
pg_dump --format=custom --file=/test/caliboo-issue25.dump
# PGDATABASE = 事前に用意した別の空の復元用DB、元DBは指定しない
pg_restore --exit-on-error --single-transaction --no-owner --dbname="$PGDATABASE" /test/caliboo-issue25.dump
# CALIBOO_DATABASE_URL も復元用DBに変更して検証（移行直後のバックアップの場合）
python -m caliboo_api.db_admin verify --snapshot /test/source.snapshot.db
```

復元後は別のAPIプロセス・ポートで起動し、下記の合成業務フローと採番を再確認する。バックアップが移行後の追加書込を含む場合は、移行元との完全一致ではなく、取得時点の記録・件数および期待する追加分を比較する。元SQLite・元PGへの上書き復元は行わない。移行前に戻す際は元SQLiteと明示設定を未変更のまま残す。PGへの新規書込後にSQLiteへ戻すとそれらの書込が欠落するため、データ同期は別途計画する必要がある。

隔離されたPGを停止するとAPI起動は失敗し、稼働中のDB依存APIは成功扱いにしない。再開後の新規セッションで取得・保存できることを確認する。コミットの成否が通信切断で不明な場合は、履歴等を再読込して結果を確認してから再操作する。

## 独立確認用の観点（レビュー用、承認済み観点の変更なし）

既存の[総合テスト観点](test-perspectives.md)を共有モードでも満たすか、以下を合成データで確認する。新規の承認記録は独立確認後に追記する。

- 既存SQLite：既定／既存パス、デモシード、管理者CLI、既存単体・統合テスト。
- 空PG：明示URL、初回構築、デモ未投入、起動時のデータ変更なし、設定誤りと停止時の非成功。
- 移行：全40表、内容・件数一致、関連行、NULL/JSON、日本語、ID/採番、既存DB拒否、失敗時ロールバック、元SQLiteを変更しないこと。
- 一つのFastAPIからの独立セッション：同一ユーザーの記録が共有され、別ユーザー本人のデータと管理者権限は従来どおり分離される。API再起動後も保持する。
- 業務回帰：日報、課題提出・フィードバック、確認待ち課題案の同時生成、クイズ集計、OJT相談・講師返信、強みの候補・承認・ジョブ取得権、パスワード管理。
- 別空DBにバックアップ復元し、検証CLIとAPIから移行時点の記録と次の採番を再確認する。

`backend/tests/unit/test_shared_database.py`は外部通信なしで設定、SQL方言・スナップショットの基本処理を検査する。別途`backend/tests/postgresql/test_shared_db.py`は一時SQLiteで生成した認証値による合成アカウントの準備処理も検証する。PostgreSQLへの接続を伴う2件は新しい空DBをローカルに明示した場合のみ実行する。テスト用パスワードは毎回メモリ内でランダム生成し、終了時に平文の参照を破棄する。PGテストはDBを自動消去しないため、再実行時は別の空DBを用意する。

```bash
# CALIBOO_TEST_POSTGRES_URL：隔離移行DB
# CALIBOO_TEST_POSTGRES_INIT_URL：隔離初期化DB（任意）
# いずれも localhost / 127.0.0.1 / ::1 + 明示ポート、caliboo_issue25_ で始まるDB名
cd backend
python -m pytest --disable-socket tests/postgresql/ -v
```

## 対象外・残作業

実運用への切替、既存の複数DBの競合解消・統合、運用DBのバックアップ方式の確定・継続運用、自動スキーマバージョン移行、クラウド/有料サービス利用、外部公開は対象外。
