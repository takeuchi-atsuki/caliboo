# TypeScript

## テストファイルの分類基準

- 仕様書（`docs/screens/*.md`等）に明文化された外部境界の振る舞いを検証するテストは `spec` 分類とする。
- 仕様書に対応がない内部実装（インフラ層等）を検証するテストは `impl` 分類とする。
- 判断に迷う場合は `impl` にフォールバックする。

## 配置規約

- テスト対象と同じディレクトリに配置する co-location 方式とする。
- ファイル名は spec分類が `<Module>.spec.ts(x)`、impl分類が `<Module>.impl.test.ts(x)` とする。

!NOTE: バックエンド(pytest)は`tests/`配下に集約する規約だが、フロントエンドはVite/Vitestのエコシステム標準に合わせ、featuresディレクトリ構成ともなじむco-location方式を採用している。

## モック方針

- 外部境界（`apiClient`等のモジュール）は`vi.mock`でモジュール単位に差し替える。
- `fetch`自体を直接モックするのは`apiClient`自身のテスト（impl分類）に限る。

## globals設定

- `globals: true` は使わず、各テストファイルで`vitest`から必要なAPIを明示的にimportする。

## カバレッジ運用

- `vite.config.ts`の`test.coverage.include`に、ロジックを持つファイル（`src/lib/apiClient.ts`のようなAPIクライアントや、カスタムhooks等）と、キー入力の判定・イベント伝播・フォーカス移動などの操作ロジックを持つコンポーネント（例: `ChatComposer.tsx`・`ReportHistoryTable.tsx`）を列挙し95%以上を維持する。
- 対象ファイルを新設・改修したら、テスト追加と`coverage.include`への追記をセットで行う。
- 見た目のみのコンポーネント(`src/components/`配下に限らず、`src/features/`配下のPage/View実装のような見た目主体のファイルも含む)は対象外とし、`docs/manual-test-cases.md`の手動確認で担保する。
