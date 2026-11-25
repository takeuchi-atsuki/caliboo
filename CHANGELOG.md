# CHANGELOG

## Unreleased

### Added

- #25: PostgreSQL 18 / psycopg 3 の明示設定による共有DB、独立した初期化・SQLiteスナップショット移行・検証手順を追加。既定のSQLite起動を維持し、共有DBの同時更新時も既存の業務制約を保持する。

- 公開リポジトリの標準GitHub Actionsランナーで、backendのlint・単体/統合テストとfrontendの型検査・テスト・ビルドを再現する品質ゲートを追加した（#32）。
- 一時SQLiteとサンドボックス有効のChromiumによる日報・再起動後の表示確認、および関連候補向けPostgreSQL 18・配布ZIP・課題導線・GUI読み込みの追加ゲートを整備した（#32）。
- 初期導入時の信頼済み検証ブランチ、最小権限、外部AI・保存されたキャッシュ/アーティファクトを使わない運用を文書化した（#32）。
