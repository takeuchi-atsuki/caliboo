# CHANGELOG

## Unreleased

### Added

- #25: PostgreSQL 18 / psycopg 3 の明示設定による共有DB、独立した初期化・SQLiteスナップショット移行・検証手順を追加。既定のSQLite起動を維持し、共有DBの同時更新時も既存の業務制約を保持する。
