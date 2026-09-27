---
name: caliboo-doc-check
description: "仕様書・ドキュメントの更新漏れを、変更パスから機械的に確認する(Caliboo版)。`dev-flow:doc-check`に加えて使う。"
when_to_use: "ドキュメント編集完了後、またはコード改修後に完了と判断する前に使う。"
---

`dev-flow:doc-check`の観点(更新漏れ・実装との不整合・参照切れ・書式規約)はそのまま使う。本skillはCaliboo固有の「どのパスを変更したらどのドキュメントを見るべきか」の対応表を追加する。

## 変更パス → 更新を検討必須のドキュメント

| 変更したパス | 更新を検討必須のドキュメント |
| --- | --- |
| `backend/src/caliboo_api/routers/**`, `schemas/**` | `docs/api.md` |
| `backend/src/caliboo_api/data/**`, `db.py`, `models.py` | `docs/architecture.md`(永続化・シード方針), `docs/api.md`の参照先記述 |
| `frontend/src/features/<x>/**` | `docs/screens/<x>.md`(home/report/ojt/study/assignment/strengths が1:1対応) |
| `frontend/src/components/**`, `styles/**`, `theme.ts` | `docs/architecture.md`(レイアウト・レスポンシブ・デザイントークン方針) |
| 外部から観測できる挙動の追加・変更 | `docs/test-perspectives.md`(手順は`caliboo-test-perspectives` skill) |
| 見た目・操作のみの変更 | `docs/manual-test-cases.md` |
| 積み残し・未決事項 | `BACKLOG.md`(`dev-flow:backlog-update` skillを使う) |
| `example/*.md` | 更新しない(PoC基本仕様書は起票時点の記録として凍結。参照のみ) |

## チェックリスト

- [ ] 上表に該当する変更パスがあれば、対応するドキュメントを更新済み、または更新不要と判断した理由を確認済みであること
- [ ] 仕様書の更新漏れがないこと
- [ ] 仕様書と実装内容が一致していること
- [ ] ドキュメント中の値(識別子・パラメータ名など)を書き換えた・削除した箇所で、編集の名目(簡略化・統一・リネーム等)によらず、その情報が他のどこからも参照できなくなっていないこと。判断に迷う場合は削除せず両方(旧値・新値)を残す
- [ ] `.claude/rules/markdown.md`(見出しは強調ではなく`#`記法を使う)・`dev-flow:doc-standard`の書式規約に沿っていること
- [ ] 仕様の追加・変更箇所のうち、後から見て「なぜその仕様か」が分からないと改修時に困りそうな箇所には`!NOTE`/`!TIP`で理由を残していること(`.claude/CLAUDE.md`参照。全箇所への記載は不要)
- [ ] `dev-flow:doc-review` skillの description・when_to_use に該当する場合は実施し、指摘それぞれについて対応要否を判断済みであること(このskillは汎用のためそのまま使う)
