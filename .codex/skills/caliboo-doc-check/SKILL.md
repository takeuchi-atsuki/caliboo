---
name: caliboo-doc-check
description: "仕様書・ドキュメントの更新漏れを、変更パスから機械的に確認する(Caliboo版)。コード・ドキュメント変更の完了前に使う。"
---

## 使用する場面

ドキュメント編集完了後、またはコード改修後に完了と判断する前に使う。

更新漏れ・実装との不整合・参照切れ・書式規約を確認する。変更パスに応じて次のドキュメントを確認する。

## 変更パス → 更新を検討必須のドキュメント

| 変更したパス | 更新を検討必須のドキュメント |
| --- | --- |
| `backend/src/caliboo_api/routers/**`, `schemas/**` | `docs/api.md` |
| `backend/src/caliboo_api/data/**`, `db.py`, `models.py` | `docs/architecture.md`(永続化・シード方針), `docs/api.md`の参照先記述 |
| `frontend/src/features/<x>/**` | `docs/screens/<x>.md`(home/report/ojt/study/assignment/strengths が1:1対応) |
| `frontend/src/components/**`, `styles/**`, `theme.ts` | `docs/architecture.md`(レイアウト・レスポンシブ・デザイントークン方針) |
| 外部から観測できる挙動の追加・変更 | `docs/test-perspectives.md`(手順は`caliboo-test-perspectives` skill) |
| 見た目・操作のみの変更 | `docs/manual-test-cases.md` |
| 積み残し・未決事項 | `BACKLOG.md`(未決事項・理由・次の対応を記録する) |
| `example/*.md` | 更新しない(PoC基本仕様書は起票時点の記録として凍結。参照のみ) |

## チェックリスト

- [ ] 上表に該当する変更パスがあれば、対応するドキュメントを更新済み、または更新不要と判断した理由を確認済みであること
- [ ] 仕様書の更新漏れがないこと
- [ ] 仕様書と実装内容が一致していること
- [ ] ドキュメント中の値(識別子・パラメータ名など)を書き換えた・削除した箇所で、編集の名目(簡略化・統一・リネーム等)によらず、その情報が他のどこからも参照できなくなっていないこと。判断に迷う場合は削除せず両方(旧値・新値)を残す
- [ ] `.codex/rules/markdown.md`(見出しは強調ではなく`#`記法を使う)の書式規約に沿っていること
- [ ] 仕様の追加・変更箇所のうち、後から見て「なぜその仕様か」が分からないと改修時に困りそうな箇所には`!NOTE`/`!TIP`で理由を残していること(`AGENTS.md`参照。全箇所への記載は不要)
- [ ] 変更内容をレビューし、不具合・回帰・確認漏れへの対応要否を判断済みであること
