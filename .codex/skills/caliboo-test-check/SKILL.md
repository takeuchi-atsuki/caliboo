---
name: caliboo-test-check
description: "テストの実施状況・カバレッジを確認する(Caliboo版)。テスト実行時と実装変更の完了前に使う。"
---

## 使用する場面

テストを実行する直前、またはコーディング完了後にテスト実施状況を確認するときに使う。

本リポジトリの`backend/tests/integration/`は一時SQLiteと`--disable-socket`で動くため、Codexが直接実行してよい。

## テスト実行コマンド

### backend 単体テスト(改修時は必ず再実行する)

```bash
cd backend && python3 -m pytest --disable-socket tests/unit/ --cov=caliboo_api --cov-report=term-missing
```

### backend 統合テスト(Codexが直接実行してよい)

```bash
cd backend && python3 -m pytest --disable-socket tests/integration/
```

!NOTE: 一時SQLite(`backend/tests/integration/conftest.py`のfixtureがテストごとに独立した一時ファイルへ切り替える)と`--disable-socket`(実ネットワーク接続を禁止する)により、実行しても外部システム・実認証情報に触れない。外部APIを使う別のテストにはこの前提を流用しない。

### frontend テスト(改修時は必ず再実行する)

```bash
cd frontend && npm run test:coverage
```

---

出力を絞る場合は`-q`・`--tb=short`等を使い、テストの終了コードを保持すること。

## 単体テストの完了確認

- [ ] テストコードが作成済みであること
- [ ] カバレッジが95%以上であること
  - backend: `--cov=caliboo_api`の出力(`TOTAL`行)で確認する
  - frontend: `vite.config.ts`の`test.coverage.thresholds`(lines/statements/branches/functions 95%)がコマンドの成否として強制する
- [ ] カバレッジ対象は改修したプロジェクト(backend/frontendのうち改修した方)のみであること
- [ ] frontendでロジックを持つファイル(`src/lib/*.ts`・`features/*/use*.ts`等のカスタムhooks・APIクライアント、およびキー入力の判定・イベント伝播・フォーカス移動などの操作ロジックを持つコンポーネント)を新設・改修した場合、`frontend/vite.config.ts`の`test.coverage.include`に追記済みであること(判断基準・配置規約・モック方針は`.codex/rules/typescript.md`に従う。見た目主体のコンポーネント・Page/View実装は対象外で`docs/manual-test-cases.md`の手動確認に委ねる)
- [ ] 全テストが成功していること

## 統合テストの完了確認

外部システムへのアクセスや複数コンポーネントにまたがる動作を変更した場合に適用する。ドキュメント変更・設定値の調整・単一コンポーネント内の修正のみであればスキップ可。

- [ ] `backend/tests/integration/`に配置されていること
- [ ] 上記コマンドで実行し、成功していること
- [ ] 新規・変更した観点が`docs/test-perspectives.md`の承認済み観点に対応していること(承認ワークフローは`caliboo-test-perspectives` skillを使う)

## その他

- [ ] 単体テストと統合テストが分離されていること(`tests/unit/`・`tests/integration/`、frontendは`.spec.ts(x)`/`.impl.test.ts(x)`)
- [ ] 変更内容をレビューし、不具合・回帰・確認漏れへの対応要否を判断済みであること
