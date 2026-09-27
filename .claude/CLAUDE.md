# 開発ルール

## 全般

- プログラムを改修した場合は、その改修内容に合わせてドキュメント類やテストコードも改訂すること

---

## 仕様書

単に仕様だけ書くのではなく、なぜその仕様なのかを!NOTEや!TIPとして追記すること。
ただし、全ての仕様に記載は不要で、後から仕様だけだと改修時に困りそうなところだけを抽出し、追記すること。

---

## 作業完了前のチェックリスト

作業完了前に必ず`dev-flow:done-check` skillを実行すること。ただし、その中で参照される`code-check`・`test-check`・`doc-check`は、本リポジトリのツールチェーン(backend: flake8/pytest、frontend: tsc/vitest。ruff・mypyは未導入)に合わせたCaliboo版へ読み替える。

| dev-flowの汎用skill | 読み替え先 |
| --- | --- |
| `code-check` | `caliboo-code-check` |
| `test-check` | `caliboo-test-check` |
| `doc-check` | `caliboo-doc-check` |

総合テスト観点の承認(テストケース作成前にユーザー承認を得て`docs/test-perspectives.md`へ記録する手順)が必要な場合は`caliboo-test-perspectives` skillを使う。
