# Codex プロジェクト設定

- 共通指示はルートの`AGENTS.md`。ファイル種別の規約はそこから`rules/*.md`を参照する。
- 設定は`config.toml`。信頼済みプロジェクトで読み込む。モデルはメインセッションの選択を維持する。
- スキルの実体は`skills/`。Codexの標準探索先`.agents/skills`から相対シンボリックリンクで参照する。
- PoC用のカスタムエージェントは`agents/*.toml`。生成・指導・レビューに`gpt-6-sol`、独立解析に`gpt-6-astra`を使用する。利用可否は実行環境で確認する。
- 編集後のカバレッジ警告は`hooks.json`と`hooks/coverage_include_warning.py`。CLIの`/hooks`で定義を確認して信頼するまで実行されない。シェル経由の編集はこのフックの対象外なので、`caliboo-test-check`でも確認する。

## 移行時の差異

旧`settings.json`・`CLAUDE.md`・Markdown形式のエージェント定義をCodex形式へ置換した。未導入の`dev-flow`への必須依存は、同梱スキルの直接実行とチェック項目に置換した。

コマンド禁止リストは`rules/commands.rules`へ移した。これはサンドボックス外のコマンド評価に用いる規則で、旧Read/Write denyと同等のファイルアクセス制御ではない。秘密ファイル等へのアクセス方針は`AGENTS.md`に残し、実行環境のサンドボックスと併用する。旧allowリストによる無条件の承認省略は移植せず、Codexの承認設定に従う。

Claude専用の環境変数・skillOverrides・plansDirectoryは削除した。利用状況の送信停止は`[analytics].enabled = false`へ移した。旧エラー報告環境変数に対応する同等設定は移植していない。

## 確認

```bash
python3 -m pytest .codex/hooks/ -q
```

設定を反映するには新しいCodexセッションを開始する。スキル一覧に5件の`caliboo-*`があることと、`/hooks`の登録を確認する。PoCの実行・API投入は設定移行の検証には含めない。

## 仕様参照

- [Codex config](https://learn.chatgpt.com/docs/config-file/config-reference)
- [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Skills](https://learn.chatgpt.com/docs/build-skills)
- [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Hooks](https://learn.chatgpt.com/docs/hooks)
