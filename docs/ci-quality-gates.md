# GitHub Actions 品質ゲート（#32）

## 対象と起動条件

[品質ゲート](../.github/workflows/quality-gates.yml)は、公開リポジトリで利用可能な標準の `ubuntu-24.04` ランナーだけで動かす。Python 3.12、Node.js 22.23.4（22.22.2以降の22系）、プロジェクトの依存定義・npm lockfile、固定版の Playwright 1.62.0 と対応する Chromium を使用する。

> [!NOTE]
> 外部投稿者の Actions 実行承認設定が未確認のため、初期導入時は main 宛PRのコードをそのまま実行せず、管理者が差分を確認した同一リポジトリの検証専用ブランチへの push のみを対象にする。forkのPRや `pull_request_target`、mainへの直接pushを起点とする実行は設定しない。外部投稿者の承認設定を確認し、実行対象を変更する場合は別途判断する。

mainから作成した検証候補に #32 を適用し、対象課題の変更も含まれていることを確認してから、承認済みの通常の方法で対応する検証ブランチに反映する。PRのマージ判断には、検証した候補の commit SHA と一致する実行結果を使用する。#32 の独立した実装ブランチに push するだけでは Actions は起動しない。

| 検証専用ブランチ（完全一致） | 候補に必須の変更 | 追加ゲート |
| --- | --- | --- |
| `ci/verify-32-base` | #32 | 共通ゲートのみ |
| `ci/verify-32-postgresql` | #25、#32 | PostgreSQL 18 |
| `ci/verify-32-package` | #29、#32 | クリーン配布ZIP |
| `ci/verify-32-assignment` | #30、#32 | ブラウザーで通常の課題導線 |
| `ci/verify-32-gui` | #26、#32 | ブラウザーで画面遷移・読み込み |
| `ci/verify-32-all` | #25、#29、#30、#26、#32 | すべての追加ゲート |

> [!NOTE]
> 検証ブランチは用途ごとに明示し、対象課題を含まない候補で追加試験が偶然スキップされた状態を合格とは扱わない。対象候補に必要なスクリプト・テスト・機能がなければ失敗させる。複数候補を組み合わせるときは、各課題が独立に作成した `CHANGELOG.md` の記載を失わないよう統合する。

## 共通ゲート

| 対象 | 実行内容と合格条件 |
| --- | --- |
| backend | flake8、単体テスト、統合テスト。単体・統合はいずれも `--disable-socket`、単体テストの分岐込みカバレッジ95%以上。 |
| frontend | `npm ci`、型検査、`npm run test:coverage`（lines/statements/branches/functions 各95%以上）、`npm run build`。`dist/index.html` と `dist/takeuchi-model.html` の両方を確認。 |
| ブラウザー | 実アプリと一時SQLiteをlocalhostで起動し、Chromiumのサンドボックスを有効化。合成管理者・新人を用い、日報を提出し、アプリ再起動と再ログイン後に表示されることを確認。 |

pytest、Vitestの各必須テスト群は終了コードだけでなく、一時レポートを検査して未実行・スキップ・0件を失敗とする。テスト時は既存の外部サービス設定やテスト選択オプションを引き継がず、バックエンドの予備DBも一時SQLiteに限定する。レポートはローカルの一時領域にのみ生成し、外部保存しない。

追加ゲートは、合成データ・ループバック通信のみで次を実行する。

- #25：PostgreSQL 18 のサービスと psycopg 3 を使用し、独立した初期化、SQLiteからの移行、実DBでの通常業務処理の同時実行とバックアップの復元を確認する。
- #29：実際の配布スクリプトでZIPを作成し、新規一時ディレクトリへの展開・セットアップ・ビルド・起動・通常の操作を確認する。
- #30：強み画面から配信課題の詳細を開く通常導線を実ブラウザーで確認する。
- #26：実ブラウザーで初期読み込みと主要画面への遷移を確認する。経過時間は参考値とし、実行環境の速度の違いだけで失敗としない。

## ローカルでの再現

Python 3.12 と Node.js 22.22.2以上の22系を用意して、リポジトリのルートから実行する。既存の開発テストと同じ入口を使用する。試験は合成データ専用・独立したローカル環境で行う。配布ZIPではなく、開発テストを含む完全なチェックアウトが必要。

```bash
python -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -e './backend[dev]'
npm ci --prefix frontend

python -m flake8 --isolated --max-line-length=100 devel/ci
python -m unittest discover -s devel/ci -p 'test_quality_gate.py'
python devel/ci/quality_gate.py backend
python devel/ci/quality_gate.py frontend

python -m pip install -r devel/ci/browser-requirements.txt
python -m playwright install --with-deps chromium
python devel/ci/browser_e2e.py
```

#30/#26 が含まれる候補では、それぞれ `--assignment`/`--gui` を追加する。両候補が含まれる場合は両方を指定できる。Chromiumをサンドボックス付きで起動できない環境では検証未完とし、サンドボックスを無効化して合格扱いにしない。

#25 の PostgreSQL 検証と #29 の配布検証は、ワークフローの専用ジョブと同じ入口を使用する。

- #25: `python devel/ci/postgres_gate.py`。使い捨ての `postgres:18` コンテナを用意し、動的ホストポートを `CALIBOO_CI_POSTGRES_PORT`、コンテナIDを `CALIBOO_CI_POSTGRES_CONTAINER`、合成のサービス初期化用パスワードを `CALIBOO_CI_POSTGRES_PASSWORD` に設定する。実運用のDBは指定しない。
- #29: `python devel/ci/package_gate.py`。PlaywrightとChromiumを準備したうえで、`release/` が存在しないクリーンな候補から実行する。ZIPや展開先は試験終了時に保存しない。

## 費用・実行範囲

- 標準GitHub-hosted runnerだけを使用する。公開リポジトリでの標準ランナーは無償。扱いは [GitHub Actions billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage) を参照する。
- 権限は `contents: read`、checkoutの資格情報永続化は無効、利用する公式Actionは40文字のcommit SHAに固定する。Actionsキャッシュと成果物アップロードは使用しない。
- 外部AI、組織の実データ、実運用の秘密情報を使わない。PostgreSQLサービスのテスト用文字列はそのジョブの合成データ用に限る。
- 依存パッケージ・ブラウザーはインストール段階で配布元から取得する。テストケースによる外部サービスへの接続は行わず、独立したテスト環境で実行する。
- リポジトリ設定の変更、ワークフローの権限回避、課金を伴うランナーや保存の追加は行わない。

## 結果の記録

検証したcommit SHA、使用したPython/Node/Playwright/ChromiumとDB版、各ジョブの終了状態、テスト件数、カバレッジ、ブラウザーの操作結果、未実行・未確認項目、実行URL（GitHub Actions実行時）を記録する。初期導入の時点でGitHub Actions自体の実行結果がない場合は、ローカルで確認できた事項と区別して扱う。

### 初期ローカル検証（2026-11-25）

共通ゲートは main `bbddd81` を起点とした #32 独立作業ブランチで検証した。Python 3.12.14、Node.js 22.22.2、npm 11.19.1、Playwright 1.62.0。Python依存は既導入のものを再利用し、npmはlockfileから新規展開した。GitHub Actionsが選択するNode.js 22.23.4での実測はまだない。最終版backendゲートは合成の環境上書き（外部設定とテスト選択オプションのダミー値）も除去して実行できた。

| 項目 | 実測結果 |
| --- | --- |
| CIスクリプト | flake8（100桁規約）成功。YAML構造・シェル構文・6つの限定起動ブランチ・最小権限・固定SHAを検査、品質ゲートの自己テスト6件成功。 |
| backend lint | flake8 7.5.0、終了コード0。 |
| backend単体 | 最終版ゲートで616件成功、JUnit件数検証・skipなし、分岐込み総合カバレッジ97.58%（基準95%）。 |
| backend統合 | 最終版ゲートで75件成功、JUnit件数検証・skipなし。`--disable-socket` で実行。 |
| frontend | Node22.22.2でクリーンな `npm ci`（282パッケージ）、型検査成功。49ファイル、334テスト成功、skipなし。Vitest 3.2.7のカバレッジは statements 99.81%、branches 97.78%、functions 99.48%、lines 99.81%。Vite 5.4.21で2つのHTML入口をビルド成功（大きいチャンクの警告あり）。 |
| SQLite | 実Uvicorn/Vite preview、通常APIで合成管理者・新人・日報の作成と再起動後の永続化、2入口のHTTP 200を部分確認。 |
| Chromium | 固定版ブラウザーの取得がHTTP 403で失敗。E2Eは未実行扱いで終了コード1。sandbox無効化・skipでの代替なし。バージョン・実画面UI操作は未確認。 |
| #25候補 `1b7fe93` | SQLite対照テスト2件成功。ローカルにDocker/PostgreSQL 18実サービスがなく、移行・独立初期化・同時処理・復元の実DB試験は未確認。 |
| #29候補 `8e06e72` | 配布回帰テスト7件成功、実配布入口が230ファイルのZIPを生成、同梱・CRC検査、新規展開、`setup.sh --venv`、frontendの2入口ビルド成功。実 `dev-server.sh` で2入口HTTP 200、初期管理者CLI、合成新人・日報の通常API操作、停止・再起動後の既定SQLite日報の保持も部分確認。Chromium未取得のため、配布ゲート全体は終了コード1。 |
| #30/#26候補 | 通常画面の導線・遅延読み込み確認を必須ゲート化。#26候補作業ツリーのビルドで分割チャンクを確認。実Chromiumでの操作・読込測定は未確認。 |
| GitHub Actions | リポジトリや外部PR承認設定を変更しておらず、GitHub上のワークフロー実行、各ゲートの実行URL、候補組み合わせ全体の合否は未確認。 |

ChromiumおよびPostgreSQLの実試験、候補を含めた検証ブランチのActions実行は、承認済みの方法で引き続き確認する。上記の部分確認のみで追加ゲートを合格とはしない。
