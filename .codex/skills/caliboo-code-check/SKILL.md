---
name: caliboo-code-check
description: "実装コードが静的解析を通過しているかを確認する(Caliboo版)。backend/frontendの実装変更後に使う。"
---

## 使用する場面

コーディング完了後、完了と判断する前に使う(backend/frontendいずれかを改修した場合)。

本リポジトリの静的解析はbackendが`flake8`、frontendが`tsc --noEmit`。ruff・mypyは未導入。

改修した側(backend/frontend)だけを実行する。両方改修した場合は両方実行する。

- [ ] backendを改修した場合: `cd backend && python3 -m flake8 src tests` が警告ゼロで通ること(`backend/.flake8`で`max-line-length=100`を設定済み)
- [ ] frontendを改修した場合: `cd frontend && npm run lint` (実体は`tsc --noEmit`) がエラーゼロで通ること
- [ ] 変更内容をレビューし、不具合・回帰・確認漏れへの対応要否を判断済みであること

各コマンドを実行し、実際の出力を確認してからチェックを入れること。出力を確認せずにチェックしてはならない。
