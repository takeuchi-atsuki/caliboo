# ホーム画面 (1b)

## 概要

ログイン後の起点となる画面。トップナビ＋マスコットを主役にしたデザイン案（デザインカンプID: 1b）を採用。

- パス: `/home`
- 実装: `frontend/src/features/home/HomePage.tsx`
- データ取得: `GET /api/home/summary`（`useHomeSummary`フック）

## 構成要素

1. `TopNav`（共通レイアウト）: ロゴ、各画面へのナビ、認証レスポンスの本人の連続学習日数、テーマ切替、表示名・ロール・アバター、ログアウト。スマートフォンでは下部ナビも表示する（[UI改善仕様](../ui-refresh.md)参照）。
2. 見出し「ホーム」と案内「今日も、自分のペースで。一歩ずつ進めていこう。」。
3. 今日の振り返り: パステル背景のカードにAPIの挨拶、`Mascot`（600px未満48px、それ以上112px、mood="happy"）と主操作「日報を書く」（`/report`へ遷移）を表示。
4. 学びの積み重ね: `DonutProgress`で資格の達成率を表示し、資格名と「学習を続ける」（`/study`）を置く。進捗と無関係な「あと少し」という断定はしない。
5. 「今日は何をしよう？」: APIのショートカットを表示する。ラベル・説明・遷移先はレスポンスを使う。
6. 今のあなたの強み: 独立したパネルに承認済み候補の可変件数のタグと「根拠と成長のヒントを見る」（`/strengths`）を表示。強みがない場合は日報や課題が材料になることを案内する。

取得待ちは骨格表示と`role="status"`、失敗時はエラーAlertを表示する。本文には`main`と見出し階層を設ける。

!NOTE: ショートカットカードの遷移先はバックエンドのレスポンス(`shortcuts[].to`)側で持たせている。フロントに固定文字列でハードコードすると、将来ルーティングを変更した際にAPI側と画面側で二重管理になるため、レスポンスの`to`フィールドをそのまま`Link`の`to`propに使う設計にした。

- ヒーローカード＋進捗カードの2カラム行、およびショートカット3枚の行は`md`(900px)未満で縦積みに切り替わる(レスポンシブ方針は`docs/architecture.md`「レイアウト・レスポンシブ方針」参照)。

## データの取得元

`GET /api/home/summary`は、ログイン中のユーザー本人のデータを次の取得元から返す（取得実装は`backend/src/caliboo_api/data/home_data.py`の`fetch_home_summary()`）。

- 表示名（`user.name`、および挨拶メッセージ`hero.message`の組み立て）: `users.display_name`
- 連続学習日数（`user.streakDays`）: ログイン中のユーザーの`home_profile`行
- 強みタグ（`strengths`）: `strength_candidates`の本人の承認済み候補
- 資格名・達成率（`certification`）: `home_profile.certification_id`が指す`certifications`行
- ショートカット（`shortcuts`）: ユーザーに依存しない固定値

## 強みの反映

強みは`strength_candidates`の本人の承認済み候補を動的表示する。候補がなければ空状態を表示し、`/strengths`で引用根拠と育成アクションを確認できる。旧`home_profile.strength*`は互換性のため残すが表示には使わない。
