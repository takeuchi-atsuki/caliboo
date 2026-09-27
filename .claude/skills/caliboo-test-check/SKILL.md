---
name: caliboo-test-check
description: "テストの実施状況・カバレッジを確認する(Caliboo版)。`dev-flow:test-check`の代わりに使う。"
when_to_use: "テストを実行する直前、またはコーディング完了後にテスト実施状況を確認するときに使う。"
---

`dev-flow:test-check`は「統合テストは実認証情報を使うためClaudeが実行してはならない」としているが、本リポジトリの`backend/tests/integration/`は一時SQLite(テストごとに独立)と`--disable-socket`(実ネットワーク禁止)で動くため、その前提が当てはまらない。Claudeが直接実行してよい。

## テスト実行コマンド

### backend 単体テスト(改修時は必ず再実行する)

```bash
cd backend && python3 -m pytest --disable-socket tests/unit/ --cov=caliboo_api --cov-report=term-missing
```

### backend 統合テスト(Claudeが直接実行してよい)

```bash
cd backend && python3 -m pytest --disable-socket tests/integration/
```

!NOTE: 一時SQLite(`backend/tests/integration/conftest.py`のfixtureがテストごとに独立した一時ファイルへ切り替える)と`--disable-socket`(実ネットワーク接続を禁止する)により、実行しても外部システム・実認証情報に触れない。`dev-flow:test-check`の「ユーザーに依頼」規定は実APIに接続する別プロジェクト前提のため、本リポジトリには適用しない。

### frontend テスト(改修時は必ず再実行する)

```bash
cd frontend && npm run test:coverage
```

---

> [!NOTE]
> パイプ(`| tail`等)やリダイレクト(`2>&1`)を付けないこと。シェル演算子を含むコマンドは`bash_guard`フックに毎回ブロックされる。出力を絞るには`-q`・`--tb=short`等のコマンド自身のオプションを使うこと。

## 単体テストの完了確認

- [ ] テストコードが作成済みであること
- [ ] カバレッジが95%以上であること
  - backend: `--cov=caliboo_api`の出力(`TOTAL`行)で確認する
  - frontend: `vite.config.ts`の`test.coverage.thresholds`(lines/statements/branches/functions 95%)がコマンドの成否として強制する
- [ ] カバレッジ対象は改修したプロジェクト(backend/frontendのうち改修した方)のみであること
- [ ] frontendでロジックを持つファイル(`src/lib/*.ts`・`features/*/use*.ts`等のカスタムhooks・APIクライアント、およびキー入力の判定・イベント伝播・フォーカス移動などの操作ロジックを持つコンポーネント)を新設・改修した場合、`frontend/vite.config.ts`の`test.coverage.include`に追記済みであること(判断基準・配置規約・モック方針は`.claude/rules/typescript.md`に従う。見た目主体のコンポーネント・Page/View実装は対象外で`docs/manual-test-cases.md`の手動確認に委ねる)
- [ ] 全テストが成功していること

## 統合テストの完了確認

外部システムへのアクセスや複数コンポーネントにまたがる動作を変更した場合に適用する。ドキュメント変更・設定値の調整・単一コンポーネント内の修正のみであればスキップ可。

- [ ] `backend/tests/integration/`に配置されていること
- [ ] 上記コマンドで実行し、成功していること
- [ ] 新規・変更した観点が`docs/test-perspectives.md`の承認済み観点に対応していること(承認ワークフローは`caliboo-test-perspectives` skillを使う)

## その他

- [ ] 単体テストと統合テストが分離されていること(`tests/unit/`・`tests/integration/`、frontendは`.spec.ts(x)`/`.impl.test.ts(x)`)
- [ ] `dev-flow:test-review` skillの description・when_to_use に該当する場合は実施し、指摘それぞれについて対応要否を判断済みであること(このskillは汎用のためそのまま使う)
