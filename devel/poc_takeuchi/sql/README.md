# Caliboo を題材にした SQLite SQL 演習

Python 標準ライブラリの `sqlite3` とメモリDBだけを使用する。`schema.sql` に4表と教材データ、`exercises.sql` に6問のSQLを保存した。制約違反とトランザクションのロールバックも `run.py` で実行する。

## 再実行

リポジトリのルートから実行する。

```bash
python3 devel/poc_takeuchi/sql/run.py
```

期待値と実測値は `exercise-results.json` と `exercise-results.md` に書き出される。1問でも不一致なら終了コード1となる。実行後の照合表示は `8/8 問一致`。

!NOTE: 未提出の判定は `score IS NULL` ではなく `submission_id IS NULL` を使う。提出済みでも未採点の点数はNULLであり、両者を混同するからである。期待値はSQLの実行結果から生成せず、`run.py` に固定した。

## 限界

教材の4人・2課題・4提出だけを検証する。実アプリのDB接続、実スキーマとの一致、並行トランザクション、性能、大量データでの動作は対象外。SQLiteのバージョンによって制約違反のエラーメッセージが変わる可能性がある。
