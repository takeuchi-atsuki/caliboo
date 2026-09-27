---
name: caliboo-code-check
description: "実装コードが静的解析を通過しているかを確認する(Caliboo版)。`dev-flow:code-check`の代わりに使う。"
when_to_use: "コーディング完了後、完了と判断する前に使う(backend/frontendいずれかを改修した場合)。"
---

`dev-flow:code-check`はruff・mypyの実行を前提にしているが、本リポジトリには導入していない(backendのdev依存は`flake8`、frontendは`tsc --noEmit`)。そのため本skillが`dev-flow:code-check`の代わりを務める。

改修した側(backend/frontend)だけを実行する。両方改修した場合は両方実行する。

- [ ] backendを改修した場合: `cd backend && python3 -m flake8 src tests` が警告ゼロで通ること(`backend/.flake8`で`max-line-length=100`を設定済み)
- [ ] frontendを改修した場合: `cd frontend && npm run lint` (実体は`tsc --noEmit`) がエラーゼロで通ること
- [ ] `dev-flow:code-review` skillの description・when_to_use に該当する場合は実施し、指摘それぞれについて対応要否を判断済みであること(このskillは汎用のためそのまま使う)

各コマンドを実行し、実際の出力を確認してからチェックを入れること。出力を確認せずにチェックしてはならない。
