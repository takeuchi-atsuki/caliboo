# ホーム画面 (1b)

## 概要

ログイン後の起点となる画面。トップナビ＋マスコットを主役にしたデザイン案（デザインカンプID: 1b）を採用。

- パス: `/home`
- 実装: `frontend/src/features/home/HomePage.tsx`
- データ取得: `GET /api/home/summary`（`useHomeSummary`フック）

## 構成要素

1. `TopNav`（共通レイアウト）: ロゴ、各画面へのナビ、右端に左から順にログイン中のユーザーの表示名・ロール、ダークモード切替ボタン、連続学習日数バッジ、ユーザーアバター、ログアウトボタン。TopNavの連続学習日数バッジは`TopNav`の`streakDays`既定値を表示するため、全ユーザーで12日固定になる（`BACKLOG.md` #23）
2. ヒーローカード: `Mascot`(size=118, mood="happy") + 挨拶メッセージ（ログイン中のユーザーの表示名から「おかえり、{表示名}さん！今日の振り返りをしよう」と組み立てる） + 「日報を書く」CTA（`/report`へ遷移）
3. 進捗カード: `DonutProgress`で資格試験の達成率を表示
4. 強みタグ: 日報AIの解析結果という想定の3タグ（`Tag`コンポーネント）
5. ショートカット3枚: 日報作成/資格勉強/OJTへの`ShortcutCard`（それぞれ`/report` `/study` `/ojt`へのリンク）

!NOTE: ショートカットカードの遷移先はバックエンドのレスポンス(`shortcuts[].to`)側で持たせている。フロントに固定文字列でハードコードすると、将来ルーティングを変更した際にAPI側と画面側で二重管理になるため、レスポンスの`to`フィールドをそのまま`Link`の`to`propに使う設計にした。

- ヒーローカード＋進捗カードの2カラム行、およびショートカット3枚の行は`md`(900px)未満で縦積みに切り替わる(レスポンシブ方針は`docs/architecture.md`「レイアウト・レスポンシブ方針」参照)。

## データの取得元

`GET /api/home/summary`は、ログイン中のユーザー本人のデータを次の取得元から返す（取得実装は`backend/src/caliboo_api/data/home_data.py`の`fetch_home_summary()`）。

- 表示名（`user.name`、および挨拶メッセージ`hero.message`の組み立て）: `users.display_name`
- 連続学習日数（`user.streakDays`）・強みタグ（`strengths`）: ログイン中のユーザーの`home_profile`行
- 資格名・達成率（`certification`）: `home_profile.certification_id`が指す`certifications`行
- ショートカット（`shortcuts`）: ユーザーに依存しない固定値

## 未実装・簡略化した点

- デザインカンプの「今のあなたの強み」タグの色・ラベルは固定3種のダミーデータ（DB(`home_profile`テーブル)へのシード投入元は`backend/src/caliboo_api/data/seed/home_seed.py`）。実際の日報AI解析ロジックは対象外(解析の仕組み自体は強み解析PoC(`docs/screens/strengths.md`)として別画面に実装済み。ホーム画面への反映は`BACKLOG.md` #3で扱う)。
