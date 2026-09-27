# Caliboo 開発ルール

- 回答・作業報告は日本語で行う。
- プログラム改修に合わせて、必要なドキュメントとテストも改訂する。
- 仕様だけでは後の改修で意図が分からなくなる箇所に、`!NOTE`や`!TIP`で理由を残す。

## ファイル種別ごとの規約

編集前に対象の規約を読む。`.codex/rules/*.md`は自動適用されないため、この指示から参照する。

- Markdown: [.codex/rules/markdown.md](.codex/rules/markdown.md)
- Python: [.codex/rules/python.md](.codex/rules/python.md)
- TypeScript/TSX: [.codex/rules/typescript.md](.codex/rules/typescript.md)

## 完了前の確認

変更対象に応じて次のskillを読み、実行結果を確認する。実行できない項目は理由を報告する。

- backend/frontendの実装変更: `.codex/skills/caliboo-code-check/SKILL.md`
- テスト実行・実装変更: `.codex/skills/caliboo-test-check/SKILL.md`
- コード・ドキュメント変更: `.codex/skills/caliboo-doc-check/SKILL.md`
- 新しい総合テスト観点が必要な仕様変更: `.codex/skills/caliboo-test-perspectives/SKILL.md`

設定・ドキュメントのみの変更ではアプリ全体のテストを必須とせず、変更した設定やスクリプトを検証する。

## アクセス方針

ユーザーが明示的に許可しない限り、`.env`・`.env.*`、`.devcontainer/ssh_config`を読み書きせず、`public/`を読まない。コマンド規則は`.codex/rules/commands.rules`に定義する。これらの指示はOSのファイルアクセス制御ではない。
