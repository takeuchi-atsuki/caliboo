# OJT画面 (1e / 1f)

## 概要

OJT（新人が課ごとのAIメンターに質問する）を2つのレイアウト案で実装している。両方とも同じデータ・ロジック（`useOjt`フック）を共有し、見た目のみ異なる。

- 1e: 課選択→AIメンター対話（1画面内でビュー切替） — パス `/ojt`、実装 `frontend/src/features/ojt/OjtChatPage.tsx`
- 1f: 課リスト＋チャット＋参照ナレッジ 3ペイン — パス `/ojt/panel`、実装 `frontend/src/features/ojt/OjtThreePanePage.tsx`

!NOTE: 1e/1fを共通の`useOjt`フックに統合したのは、「課選択」「チャット送受信」というドメインロジックがデザイン差分と無関係だから。ロジックを2重実装すると、将来課データの取得方法を変えた際に片方だけ直し忘れるバグを誘発しやすい。

## データ・API

- `GET /api/ojt/departments`: 課一覧（開発課/品質保証課/営業課/設計課/製造課/総務課の6件、固有アイコン・色・ナレッジ件数を保持）
- `GET /api/ojt/departments/{id}/messages`: 選択した課の初期チャット履歴（bot発言1件）
- `GET /api/ojt/departments/{id}/knowledge`: 選択した課の参照ナレッジ一覧（1fの右ペインのみ使用）
- `POST /api/ojt/chat`: チャット送信→ダミー応答（`build_ojt_reply`がテンプレート文字列を生成）

DB(`departments`/`department_messages`/`knowledge_items`テーブル)へのシード投入元は`backend/src/caliboo_api/data/seed/ojt_seed.py`、取得実装は`backend/src/caliboo_api/data/ojt_data.py`の`fetch_departments()`/`get_department()`/`get_initial_messages()`/`get_knowledge()`。

## 1e固有の挙動

- 課カードをクリックすると`selectDept`が呼ばれ、画面内state（`selectedDeptId`）を切り替えることで「課選択ビュー」→「チャットビュー」に遷移する（URLは変えない）。
- チャットビューの「戻る」ボタンで`backToDeptList`を呼び、課選択ビューに戻る。

!NOTE: 課カードは`CardActionArea`/`ListItemButton`、「戻る」ボタンは`IconButton`という実際のインタラクティブ要素で実装し、Tab/Enter/Spaceキーのみでも操作できるようにしている。

- 課選択グリッドは`md`(900px)未満で1カラム、`md`以上で3カラムに切り替わる(レスポンシブ方針は`docs/architecture.md`「レイアウト・レスポンシブ方針」参照)。

## 1f固有の挙動

- 画面表示時に自動的に最初の課（`departments[0]`）を選択状態にする（`useEffect`）。1eと違い、常に3ペインが同時に見えている設計のため、「未選択」の空状態を極力減らす目的。
- 左の課リストをクリックすると中央チャット・右ナレッジが選択課の内容に切り替わる。
- `md`(900px)未満では左ペイン(課をえらぶ)・右ペイン(参照ナレッジ)が`CollapsibleAside`によりオーバーレイのドロワーに切り替わり、中央チャットヘッダーのアイコンボタン(左:`ph-list`、右:`ph-books`)で個別に開閉する。左ドロワーは課を選択すると同時に自動的に閉じる。

!NOTE: 右ペイン(参照ナレッジ)は選択操作を伴わないため、左ペインと違い自動クローズの仕組みを持たない。ユーザーの明示的な操作(背景タップ・Escキー・閉じるボタン)で閉じる。

!NOTE: 左右のドロワーは独立した開閉状態を持つが、片方を開いている間はそのドロワーの背景(バックドロップ)が中央チャットヘッダーごと覆うため、もう一方のトリガーアイコンをクリックできず、両方を同時に開くことはUI操作上できない(先に開いている方を閉じない限り、もう一方を開けない)。

## 未実装・簡略化した点

- チャット履歴はフロント側のstateのみで保持し、サーバー側では会話ログを保存しない（`POST /api/ojt/chat`はリクエストの`text`から都度ダミー応答を生成するだけ）。
