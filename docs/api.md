# バックエンドAPI仕様

FastAPIアプリ本体: `backend/src/caliboo_api/main.py`。CORS設定は持たない(開発時はViteの`server.proxy`で`/api`を転送し、画面と同一オリジンで呼び出す。理由は`docs/architecture.md`「認証・認可」参照)。

`POST /api/auth/login`・`POST /api/auth/logout`以外の全エンドポイントはログイン必須で、未認証(Cookie無し・無効・期限切れ)の場合は401 `{"detail": "not authenticated"}`を返す。ロールによる権限不足は403 `{"detail": "forbidden"}`。ユーザーごとのデータ(ホーム・資格勉強の進捗・日報・課題の提出)は、ログイン中のユーザーのものだけを返す。分野別進捗率は`user_progress_categories`の本人行を返す。

## 認証

| Method | Path | 説明 |
|---|---|---|
| POST | /api/auth/login | `{"loginId": "yuki", "password": "..."}`で認証し、セッションCookie(`caliboo_session`)を設定してログイン中のユーザーを返す。ログインIDまたはパスワードの誤りは401 `{"detail": "invalid login id or password"}`(どちらの誤りかは区別しない)。`loginId`は前後空白を除いたうえで空なら422。`password`は空文字なら422で、前後空白は除かない(空白のみのパスワードは422ではなく401) |
| POST | /api/auth/logout | セッションを破棄しCookieを削除する。204。認証不要で冪等(Cookieが無い・期限切れでも204) |
| GET | /api/auth/me | ログイン中のユーザーを返す。未認証は401 |

`login`・`me`のレスポンス(`schemas/auth.py`の`CurrentUser`):

```json
{ "id": 1, "loginId": "yuki", "displayName": "ユウキ", "role": "member", "streakDays": 12 }
```

`role`は`"member"`(新入社員)|`"admin"`(講師)。開発用アカウントは`docs/screens/login.md`を参照。

!NOTE: ログアウトを認証不要・冪等にしているのは、期限切れのセッションでログアウトを押した場合に401を返すと、画面側がエラーとして扱うか成功として扱うかの判断が必要になるため。ログアウトの目的(セッションとCookieが残らないこと)はどの状態からでも達成できる。

!NOTE: バックエンドはSQLiteでDB永続化する。参照系エンドポイントはアプリ起動時にシード投入されたDBの値を返し、`POST /api/report`はDBの`reports`テーブルへ保存する。設計理由は`docs/architecture.md`を参照。

## ホーム

### GET /api/home/summary

画面1(ホーム)の初期表示データを返す。

レスポンス例は`backend/src/caliboo_api/schemas/home.py`の`HomeSummary`、DBアクセス実装は`data/home_data.py`(`fetch_home_summary()`)、初期シード値は`data/seed/home_seed.py`を参照。

`shortcuts`はユーザー共通の固定値で、「課題に取り組む」（`/assignments`）・「資格勉強」（`/study`）・「OJT」（`/ojt`）の順に返す。日報への導線はホームのふり返りパネルに置く。

## 日報

### POST /api/report

リクエスト（`schemas/report.py`の`ReportRequest`）:

```json
{
  "date": "2026-07-15",
  "keep": "...",
  "problem": "...",
  "try": "...",
  "mood": ["fun", "tired"],
  "moodComment": "...",
  "status": "draft"
}
```

`mood`は`"happy"|"fun"|"foggy"|"tired"`から0個以上を選んだ配列(複数選択可)、`status`は`"draft"|"submitted"`。

レスポンス: `{ "id": "rpt_20260715_1", "status": "draft", "savedAt": "2026-07-15T..." }`

### GET /api/report/history

提出済み(`status == "submitted"`)の日報を、`date`降順(同一`date`は提出順=新しい方が先)で返す。

```json
{
  "history": [
    {
      "date": "2026-07-20",
      "keep": "朝イチでタスクを整理したら集中できた",
      "problem": "会議の発言タイミングがつかめなかった",
      "try": "次の会議で1回は質問してみる",
      "mood": [],
      "moodComment": ""
    },
    {
      "date": "2026-07-10",
      "keep": "keep",
      "problem": "problem",
      "try": "try",
      "mood": ["tired"],
      "moodComment": "少し疲れた一日だった"
    }
  ]
}
```

### GET /api/report/drafts

保存済みの下書き(`status == "draft"`)を、`savedAt`降順・同一`savedAt`は`id`降順（直近に保存したものが先頭）で返す。

```json
{
  "drafts": [
    {
      "id": 3,
      "date": "2026-07-22",
      "savedAt": "2026-07-22T09:00:00+00:00",
      "keep": "keep",
      "problem": "problem",
      "try": "try",
      "mood": ["happy"],
      "moodComment": "moodComment"
    }
  ]
}
```

### DELETE /api/report/drafts/{id}

下書きを1件削除する。`id`は`GET /api/report/drafts`が返す`id`（数値）。

- 対象が存在しない、または`status == "submitted"`（提出済み）の場合は404を返す（提出済みレコードの誤削除防止）。
- 他のユーザーの下書きを指定した場合も404を返す（403にしないのは、他人の下書きIDが存在すること自体を知らせないため）。
- 成功時は204(No Content、ボディなし)を返す。

## OJT

| Method | Path | 説明 |
|---|---|---|
| GET | /api/ojt/departments | 部署一覧（初期6件、追加可能）。各部署はid/name/icon/color/knowledgeCount/quickAsks。件数は登録ナレッジの実件数 |
| POST | /api/ojt/departments | adminのみ。部署を追加して設定を返す（201）。ID重複は409 |
| GET | /api/ojt/departments/{dept_id}/configuration | adminのみ。部署設定とrevisionを取得。未知の部署は404 |
| POST | /api/ojt/departments/{dept_id}/configuration | adminのみ。revision一致時に設定を一括更新（200）。未知の部署は404、競合は409 |
| GET | /api/ojt/departments/{dept_id}/messages | 指定部署の現在の初期案内＋本人の保存済み履歴、escalated。存在しないdept_idは404 |
| GET | /api/ojt/departments/{dept_id}/knowledge | 指定課の参照ナレッジ一覧。存在しないdept_idは404 |
| POST | /api/ojt/chat | `{"deptId": "...", "text": "..."}` を受け取りダミー応答を返す。存在しないdeptIdは404 |

部署設定の共通入力は次のとおり。作成時は `id`、更新時は取得済みの `revision`（1以上の整数）を加える。更新時に `id` は送らない。応答は共通入力に `id` と保存後の `revision` を加えたもの。

```json
{
  "name": "研究課",
  "icon": "ph ph-code",
  "color": "#d6ebff",
  "welcomeMessage": "研究課の相談窓口です。",
  "quickAsks": ["記録の残し方は？", "相談先は？"],
  "replyGuidance": "判断に迷う場合は担当講師に確認してください。",
  "knowledge": [{"title": "実験記録", "description": "条件と結果を記録してください。"}]
}
```

全フィールド必須。`quickAsks`・`knowledge` は空配列、`replyGuidance` は空文字を許可する。部署IDは `^[a-z][a-z0-9-]{0,39}$`、部署名1〜100文字、初期案内1〜4000文字、補足案内0〜4000文字。質問候補は最大8件（各1〜200文字）、ナレッジは最大100件（タイトル1〜200文字・説明1〜4000文字）。必須テキストの前後空白を除去し、空白だけの入力を拒否する。

アイコンは `ph ph-code` / `ph ph-shield-check` / `ph ph-handshake` / `ph ph-compass-tool` / `ph ph-factory` / `ph ph-briefcase`、色は `#d6ebff` / `#cdeede` / `#ffd9e6` / `#e3ddff` / `#ffe9c7` / `#f4f0ec`。不正値・未知のフィールドは422。管理APIの未認証は401、memberは403。

保存は全設定を単一トランザクションで更新し、成功ごとに `revision` を1増やす。更新競合では一部の項目も変更しない。起動時に不足設定だけを追加し、履歴・返信・配属と保存済み設定を保持する。実装は `data/ojt_configuration.py`・`schemas/ojt.py`。設計理由は [部署別OJTフレームワーク](ojt-framework.md) を参照。自動回答は従来のテンプレートに `replyGuidance` を平文で追加するだけで、ナレッジ検索やLLM連携は行わない。

## 資格勉強

| Method | Path | 説明 |
|---|---|---|
| GET | /api/study/progress | 資格名・分野別進捗・連続学習日数 |
| GET | /api/study/related-questions | 関連過去問一覧(タグ付き) |
| POST | /api/study/chat | `{"text": "..."}` を受け取りダミー応答を返す |
| GET | /api/quiz/next?category=&excludeId= | 次の出題。`category`一致する問題群からランダムに1問返す。正解・解説は含まない。`excludeId`を指定すると、除外後に候補が残る限りそのIDの問題は返さない(直前の問題の連続出題を防ぐ) |
| POST | /api/quiz/answer | `{"questionId": "...", "selectedIndex": 0}` を受け取り正誤判定結果を返す。存在しないquestionIdは404 |

## 課題演習

ロールごとに可能な操作は`docs/screens/assignment.md`「ロール(新入社員/講師)」を参照。`status`/`submission`は、ロールによらず常に呼び出したユーザー本人の提出を表す(講師は常に未提出/`null`)。

| Method | Path | 説明 |
|---|---|---|
| GET | /api/assignments | 課題一覧。作成日時降順(同値はid降順)。講師は全課題、新入社員は全員宛て+自分宛ての課題のみ |
| GET | /api/assignments/{assignment_id} | 課題詳細+本人の提出/フィードバック。存在しないID・他人宛ての課題は404 |
| POST | /api/assignments | 課題作成(講師のみ。新入社員は403) |
| POST | /api/assignments/{assignment_id}/submission | 本人の回答提出(新入社員のみ。講師は403)。フィードバック確定前は上書き再提出可 |
| GET | /api/assignments/{assignment_id}/submissions | 新入社員の提出一覧(講師のみ。新入社員は403)。全員宛てなら新入社員全員、個人宛てなら対象者のみ |
| POST | /api/assignments/{assignment_id}/submissions/{user_id}/feedback | 指定した新入社員の提出へのフィードバック保存(講師のみ。新入社員は403)。上書き可 |

`POST /api/assignments`のリクエスト(`schemas/assignment.py`の`AssignmentCreateRequest`):

```json
{ "title": "ビジネスメールの書き方をまとめよう", "body": "社外の取引先へ送る依頼メールを想定し..." }
```

`POST /api/assignments/{assignment_id}/submission`のリクエスト(`AssignmentSubmissionRequest`):

```json
{ "answerText": "件名は要件が一目で分かる短い文にし..." }
```

`POST /api/assignments/{assignment_id}/submissions/{user_id}/feedback`のリクエスト(`AssignmentFeedbackRequest`):

```json
{ "comment": "結論から書く構成になっていて読みやすいです。" }
```

課題作成・回答提出は、成功時に課題詳細(`AssignmentDetail`)全体を返す(フロントが追加のGETなしで画面を最新化できるようにするため):

```json
{
  "id": 1,
  "title": "ビジネスメールの書き方をまとめよう",
  "body": "社外の取引先へ送る依頼メールを想定し...",
  "status": "reviewed",
  "createdAt": "2026-09-01T09:00:00+00:00",
  "target": null,
  "messageForMember": null,
  "submission": {
    "answerText": "件名は要件が一目で分かる短い文にし...",
    "submittedAt": "2026-09-02T10:30:00+00:00",
    "feedbackComment": "結論から書く構成になっていて読みやすいです。",
    "feedbackAt": "2026-09-03T14:00:00+00:00"
  }
}
```

`status`は`"not_submitted"`(未提出)|`"submitted"`(レビュー待ち)|`"reviewed"`(フィードバック済み)。`submission`は未提出の場合`null`。

`target`は配信先で、全員宛ての課題は`null`、個人宛ての課題(手動作成または課題案から配信)は`{ "id": 3, "displayName": "ハルカ" }`。一覧(`GET /api/assignments`)の各要素にも含む。`messageForMember`(詳細のみ)は講師から対象者へのひとことで、全員宛て・未入力の場合は`null`。

!NOTE: 課題が課題案から配信されたかどうか(由来)はこのAPIに出さない。新入社員に「AIが作った」ことを見せない方針(`docs/screens/assignment.md`「AIの課題案」)のため。講師が課題から元の課題案を引くときは`GET /api/assignment-proposals?assignmentId=`を使う。

`GET /api/assignments/{assignment_id}/submissions`は、全員宛ての課題なら`role`が`member`の全ユーザーを表示名の昇順(同値はid昇順)で、未提出者も含めて返す。個人宛ての課題なら対象者1人のみを返す。フィードバック保存は、成功時にこの一覧の要素(`MemberSubmission`)1件を返す:

```json
{
  "submissions": [
    {
      "user": { "id": 2, "displayName": "ソラ" },
      "status": "not_submitted",
      "submission": null
    },
    {
      "user": { "id": 1, "displayName": "ユウキ" },
      "status": "reviewed",
      "submission": {
        "answerText": "件名は要件が一目で分かる短い文にし...",
        "submittedAt": "2026-09-02T10:30:00+00:00",
        "feedbackComment": "結論から書く構成になっていて読みやすいです。",
        "feedbackAt": "2026-09-03T14:00:00+00:00"
      }
    }
  ]
}
```

!NOTE: 未提出者も一覧に含めるのは、講師が「誰がまだ提出していないか」を把握できるようにするため。提出行だけを返すと、未提出者は一覧に現れず気づけない。

異常系:

- タイトル・課題文・回答・コメントが空文字(空白のみを含む)の場合は422。
- 存在しない`assignment_id`を指定した場合は404(詳細取得・提出・提出一覧・フィードバックいずれも)。新入社員が他人宛ての課題の詳細取得・提出をした場合も404。
- フィードバックで、存在しない`user_id`、`role`が`member`でないユーザーの`user_id`、または個人宛て課題の対象者でない`user_id`を指定した場合は404。
- ロールの判定は存在確認より先に行う(新入社員が存在しない課題の提出一覧を要求した場合も403)。
- フィードバック確定済み(`reviewed`)の課題への提出は409。
- 未提出(`not_submitted`)の課題へのフィードバックは409。

## AIの課題案

講師専用(新入社員は403)。画面仕様・生成のしくみは`docs/screens/assignment.md`「AIの課題案」を参照。

| Method | Path | 説明 |
|---|---|---|
| GET | /api/assignment-proposals | 課題案一覧+新入社員一覧+確認待ち件数。`?status=pending|approved|rejected`(省略時`pending`)、`?assignmentId=`(指定時は状態によらず、その課題を配信した課題案のみ) |
| POST | /api/assignment-proposals | 指定した新入社員の課題案を生成。新規は201、確認待ちが既にあればそれを200で返す |
| GET | /api/assignment-proposals/{proposal_id} | 課題案の詳細 |
| POST | /api/assignment-proposals/{proposal_id}/approve | 講師が確認・編集した内容で課題を作成し、対象者1人に配信する |
| POST | /api/assignment-proposals/{proposal_id}/reject | 見送る(理由は任意) |

`GET /api/assignment-proposals`のレスポンス(`proposals`は作成日時降順、同値はid降順。`members`は`role`が`member`のユーザーを表示名順。`pendingCount`は確認待ちの課題案の件数):

```json
{
  "proposals": [
    {
      "id": 1,
      "target": { "id": 3, "displayName": "ハルカ" },
      "title": "報告の構成を整理してみよう",
      "aim": "結論から伝える報告の型を身につける",
      "status": "pending",
      "createdAt": "2026-09-25T09:00:00+00:00",
      "decidedAt": null
    }
  ],
  "members": [
    { "id": 2, "displayName": "ソラ", "hasPending": false },
    { "id": 3, "displayName": "ハルカ", "hasPending": true }
  ],
  "pendingCount": 1
}
```

`POST /api/assignment-proposals`のリクエスト:

```json
{ "userId": 3 }
```

`POST /api/assignment-proposals/{proposal_id}/approve`のリクエスト(`title`・`body`は空不可、`messageForMember`は空可):

```json
{ "title": "報告の構成を整理してみよう", "body": "...", "messageForMember": "報告の組み立て方を一緒に練習してみましょう。" }
```

`POST /api/assignment-proposals/{proposal_id}/reject`のリクエスト:

```json
{ "reason": "来週の面談で直接扱うため" }
```

生成・詳細取得・配信・見送りは、成功時に課題案の詳細を返す(一覧の要素の項目に加えて以下を持つ):

```json
{
  "id": 1,
  "target": { "id": 3, "displayName": "ハルカ" },
  "title": "報告の構成を整理してみよう",
  "aim": "結論から伝える報告の型を身につける",
  "status": "approved",
  "createdAt": "2026-09-25T09:00:00+00:00",
  "decidedAt": "2026-09-25T10:00:00+00:00",
  "body": "...",
  "messageForMember": "...",
  "rationale": "...",
  "estimateMinutes": 30,
  "materials": [
    { "kind": "report", "date": "2026-09-22", "quote": "報告で結論が後回しになり、聞き返された。", "sourceLabel": "日報 Problem" }
  ],
  "progress": { "submittedCount": 0, "reviewedCount": 0, "notSubmittedCount": 3, "recentMoods": ["foggy", "tired", "foggy"] },
  "generator": "rule_based_v1",
  "assignmentId": 4,
  "rejectReason": null,
  "decidedBy": { "id": 4, "displayName": "佐藤先生" },
  "edited": true
}
```

- `status`は`"pending"`(確認待ち)|`"approved"`(配信済み)|`"rejected"`(見送り)。
- `title`・`body`・`messageForMember`は生成時の内容のまま変わらない(`messageForMember`は生成時に空なら`null`)。配信した内容は`assignmentId`の課題(`GET /api/assignments/{assignment_id}`)にあり、`edited`は配信した内容が生成時の内容と異なる場合に`true`(確認待ち・見送りでは`false`)。
- `materials[].kind`は`"report"`(日報)|`"feedback"`(講師フィードバック)|`"mood"`(直近のきもち)|`"progress"`(課題の進捗)。`date`は気分・進捗の材料では`null`。フィードバック材料の`date`は日本時間(`Asia/Tokyo`)の日付。フィードバック確定前(`feedback_at`未設定)は`null`。

!NOTE: 日付を日本時間基準にしているのは、UTC基準のまま日付だけ切り出すと日本時間の日付と1日ずれる場合があるため(他のAPIのタイムスタンプ自体はUTCのまま`+00:00`で返す。日付のみへ変換する箇所に限った対応)。
- `progress`は生成時点の状況(提出数・フィードバック済み数・未提出数・直近5件の日報のきもち)。
- `generator`は生成に使った生成器の名前。

異常系:

- `status`が不正な値の場合は422(`assignmentId`を指定して`status`の値が使われない場合も検証する)。
- 生成で、存在しない`userId`、または`role`が`member`でないユーザーの`userId`を指定した場合は404。
- 存在しない`proposal_id`を指定した場合は404。
- 確認待ち以外の課題案の配信・見送りは409。
- 配信時に`title`・`body`が空文字(空白のみを含む)の場合は422。

## 強み解析PoC

OJTの作業ログ・日報・レビューから強みを解析するPoC(`docs/screens/strengths.md`、基本仕様書は`example/Caliboo_強み解析_PoC_機能追加_基本仕様書.md`)。

!NOTE: `example/`配下の基本仕様書は起票時点(2026-09-24)の記録として凍結し、実装と一致させる正典は本書および`docs/screens/strengths.md`とする。基本仕様書§6のAPI表からは意図的に次の点が異なる: (1)非同期ジョブ化(ポーリング/webhook)を採らず`POST /runs`を同期実行にした、(2)HITL用の`POST /runs/{id}/feedback`は実装しない、(3)デモシナリオ選択のため`GET /personas`と一覧取得の`GET /runs`を追加した。理由は後述および`docs/architecture.md`を参照。

ログインしていればロールに関係なく呼び出せる(runの被験者は台本上のペルソナで、実ユーザーに紐づかないため)。外部から`POST /api/poc/runs/import`を呼ぶ場合も、先に`POST /api/auth/login`でセッションCookieを取得する必要がある(手順は`.claude/skills/caliboo-strength-run/SKILL.md`「HTTP呼び出し方法」)。

| Method | Path | 説明 |
|---|---|---|
| GET | /api/poc/personas | デモシナリオ一覧(3件)を返す |
| POST | /api/poc/runs | `{"personaKey": "..."}`を受け取りパイプラインを同期実行し、完了したrun詳細を返す。未知のpersonaKeyは404 |
| POST | /api/poc/runs/import | 外部(Claude Codeセッション等)で生成したtrajectory・日報・レビューを受け取り、Fan-in統合・解析・永続化を行う。バリデーション違反は422 |
| GET | /api/poc/runs | run一覧を新しい順に返す(run詳細の中身は含まない) |
| GET | /api/poc/runs/{run_id} | run詳細(軌跡・日報・レビュー・Strength JSON)。存在しない/不正な形式のIDは404 |
| GET | /api/poc/runs/{run_id}/diary | 生成された日報のみ |
| GET | /api/poc/runs/{run_id}/reviews | 3職種レビューとFan-in統合結果 |
| GET | /api/poc/runs/{run_id}/strengths | Strength JSON |

`run_id`は`run_0001`形式(DBの連番を4桁ゼロ詰め)のみを受理する。`run_1`のような非正規形式は、数値としては同じ行を指していても404になる(同一リソースを指す複数URLの並立を避けるため)。`status`は常に`"completed"`を返す。

!NOTE: `POST /runs`を同期実行にしたのは、本PoCの生成が事前執筆の台本+決定論的な解析で完結し、実行が一瞬で終わるため(基本仕様書§6は実LLM呼び出しの待ち時間を前提に非同期化を想定していた)。実LLM連携へ差し替える際は、このエンドポイントの非同期化が必要になる。

### POST /api/poc/runs/import

`docs/architecture.md`が述べる通り、アプリ実行時にLLMを呼ぶ経路は無いが、開発セッションのClaude自身が①〜③(生成)を担い、その結果を投入する経路として用意している(`.claude/skills/caliboo-strength-run/`から起動)。Fan-in統合・④解析・永続化は`POST /runs`(台本経由)と同じ実装(`services/poc_strength/pipeline.py`の`_assemble_run()`)を通るため、解析ロジック自体は共有する。

リクエスト例:

```json
{
  "personaKey": "external_claude",
  "subjectId": "emp_101",
  "label": "Claude生成run(SQLが強い新人)",
  "injectedPersona": "SQL/データ処理が強い新人",
  "trajectory": [
    {
      "iteration": 1,
      "task": { "taskId": "ext_1", "title": "受注データの集計", "description": "...", "skillHint": "DBAD" },
      "workerOutput": "...",
      "trainerFeedback": "...",
      "humanOverride": null
    }
  ],
  "diary": {
    "date": "2026-09-24",
    "tasks": [{ "time": "09:30-12:00", "what": "...", "progressDesc": "...", "progressRate": 100 }],
    "feelings": { "emotion": "...", "trigger": "...", "nextAction": "..." },
    "kpt": { "keep": "...", "problem": "...", "try": "..." }
  },
  "reviews": [
    { "agentKey": "alpha", "reviewerRole": "管理職", "magiTone": "MELCHIOR", "comment": "...", "flags": [] }
  ],
  "trace": {
    "generationProvider": "claude_session",
    "agents": [{ "key": "strength-worker", "model": "sonnet", "promptVersion": "2026-09-24.1" }]
  },
  "externalStrengths": null
}
```

フィールドの要点:

- `personaKey`は省略可(既定`"external_claude"`)。デモシナリオ選択(`GET /personas`)の一覧には出ない。
- `diary`に`mentorComment`は含めない。サーバー側がFan-in統合結果で補完する(`PocDiary`との違い)。
- `trace.agents`は生成を担ったエージェント定義の記録(`key`/`model`/`promptVersion`)。`analysisProvider`は受け取らず、サーバー側が確定させる。
- `externalStrengths`(任意)は、ルールベース解析(`RuleBasedAnalysisProvider`)とは別モデルの解析エージェントが出した`StrengthOutput`。指定すると`trace.externalAnalysis`にそのまま格納され、ルールベース解析結果(`strengths`)とは独立に保持される(仕様書§2「評価者の分離」)。

異常系:

- `trajectory`が3件でない、または`iteration`が1→2→3の連番でない場合は422(仕様書§5「3回固定」)。
- `reviews`の`agentKey`が`alpha`/`beta`/`gamma`と過不足なく一致しない場合は422(順序は問わない)。
- `diary.tasks`が空配列の場合は422。
- `subjectId`/`label`/`trace.generationProvider`・`trajectory[].task`の各フィールド・`workerOutput`/`trainerFeedback`・`diary`配下の各文字列フィールド・`reviews[].reviewerRole`/`magiTone`/`comment`など、主要な文字列フィールドが空文字(空白のみを含む)の場合は422。

レスポンスは`POST /runs`と同じ`PocRunDetail`。ただし`trace.scriptVersion`は常に`null`になり、代わりに`trace.agents`が設定される(台本経由と外部投入経由の切り分けは`trace`のこの2フィールドで判別できる)。

`GET /api/poc/runs/{run_id}/strengths`のレスポンス例(抜粋):

```json
{
  "subjectId": "emp_001",
  "runId": "run_0001",
  "generatedAt": "2026-09-24T00:00:00+00:00",
  "provider": "rule_based_v1",
  "strengths": [
    {
      "id": "st_dbad",
      "layerTask": { "framework": "SFIA", "skillCode": "DBAD", "skillName": "データベース設計/管理", "level": 2 },
      "layerBehavior": { "framework": "CliftonStrengths", "themes": ["Analytical", "Deliberative"] },
      "layerWillSkill": { "quadrant": "High Will / High Skill", "policy": "意欲・技能とも揃っているため、応用範囲を広げる課題で伸ばす" },
      "confidence": 0.85,
      "status": "confirmed",
      "evidence": [
        {
          "quote": "受注データの集計クエリを作成しました。",
          "source": { "kind": "trajectory", "iteration": 1, "field": "workerOutput", "role": null }
        }
      ],
      "learningAgility": { "delta": "0", "note": "1周目から2周目にかけて、安定して現れている" },
      "growthContent": { "title": "SQL・データ処理の課題", "contentTag": "sql-drill" }
    }
  ],
  "overallStatus": "partial",
  "notes": "根拠が揃わない領域は暫定・評価保留とした"
}
```

### 判定ルール

解析は`services/poc_strength/analysis.py`の決定論的なルールで判定する。しきい値・対応表は`services/poc_strength/skill_catalog.py`に集約する。

- 裏付けの種類: スキル辞書のキーワードが、軌跡(成果物・指導者の所見・課題文) / 日報 / レビューの各テキストに現れたかを種類ごとに判定する。1つも現れないスキルは`strengths`に出力しない。
- `confidence`と`status`: 裏付け3種類=0.85・`confirmed`、2種類=0.6・`tentative`、1種類=0.35・`insufficient_evidence`。
- `layerTask.level`: 裏付け3種類なら2、それ以外は1(新入社員を対象とする前提のため1〜2のみ)。
- `learningAgility.delta`: そのスキルへの言及があった周回のうち、最初と最後の周回でキーワードの種類数を比較する。増=`+` / 同=`0` / 減=`-`。言及があった周回が1つ以下の場合は`0`とし、note に評価できない旨を入れる。
- `layerWillSkill`: Will軸は`delta`が`+`、または`0`かつ複数周で継続して観測できた場合に High。Skill軸は`level`が2以上で High。
- `layerWillSkill`と`growthContent`は、`insufficient_evidence`の強み、および複数周で観測できずWill軸を評価できなかった強みでは`null`になる。
- `overallStatus`: 1件以上ありすべて`confirmed`なら`complete`、0件またはすべて`insufficient_evidence`なら`insufficient`、それ以外は`partial`。`notes`は`overallStatus`から一意に決まる。
- `strengths`の並びはスキル辞書の定義順(確信度の降順ではない)。
- `id`は`st_` + `skillCode`の小文字。
- `evidence`は裏付けの種類ごとに1件まで(最大3件)。引用は本文を句点で区切った最初の一致文で、優先順位は 本人の成果物 → 指導者の所見 → 課題文。
- `evidence.source.kind`は`trajectory` / `diary` / `review`。`iteration`は`trajectory`のみ、`role`は`review`のみ設定される。

!NOTE: Will軸に`confidence`を使わないのは、確からしさは意欲の高さではないため。流用すると根拠の薄い強みが自動的に「意欲は高いが技能が低い」と断定される。同じ理由で、複数周で観測できず評価できない場合は「意欲が低い」とせず象限ごと空にする(根拠が無いものを断定しないという方針は確信度だけでなくWill軸にも及ぶ)。

!NOTE: Fan-inの統合コメントは`diary.mentorComment`に入れる一方、解析の日報テキストからは除外する。中身は3職種レビューの全文であり、含めるとレビュー種別と同じ文章を二重に数えて暫定が確定へ繰り上がるため。解析にはFan-in前の3職種コメントを個別に渡す(どの職種の所見が根拠かを`evidence.source.role`で示すため)。

### 基本仕様書§4のキー名との対応

基本仕様書§4のJSON例はsnake_caseだが、本APIは既存の他エンドポイントと同じcamelCaseに統一している(基本仕様書自身が§4を「PoC用の論理スキーマ(確定前提でなく叩き台)」と位置づけているため)。対応は次の通り。

| 基本仕様書§4 | 本API | 備考 |
|---|---|---|
| `subject_id` / `run_id` / `generated_at` | `subjectId` / `runId` / `generatedAt` | |
| `layer1_task` / `layer2_behavior` / `layer3_will_skill` | `layerTask` / `layerBehavior` / `layerWillSkill` | 層の番号は名前から落とした |
| `skill_code` / `skill_name` | `skillCode` / `skillName` | |
| `evidence[].source`(文字列パス) | `evidence[].source`(オブジェクト) | `{kind, iteration, field, role}`に構造化 |
| `learning_agility` / `overall_status` | `learningAgility` / `overallStatus` | |
| `layer2_behavior.big_five` | (出力しない) | キーワード出現から性格特性の連続値を断定するのは根拠として弱いため |
| (対応なし) | `layerWillSkill.policy` / `growthContent` | §7の育成アクション連携に対応して追加 |
| (対応なし) | `provider` | 解析に使ったプロバイダ名(トレーサビリティ) |

## 動作確認方法

依存パッケージは事前に`bash ./devel/setup.sh`でインストールしておく(`devel/README.md`参照)。ホスト環境で`setup.sh`を実行した場合は依存が`backend/.venv`に入るため、`cd backend`の後に`source .venv/bin/activate`で有効化してから以下を実行する(Dev Containerでは不要)。

```bash
cd backend
python -m pytest --cov=caliboo_api --cov-report=term-missing  # 単体テスト・カバレッジ確認
python -m pytest tests/integration/                            # 総合テスト
python -m flake8 --max-line-length=100 src tests               # 静的解析
python -m uvicorn caliboo_api.main:app --reload --port 8000     # 開発サーバー起動
```

開発サーバーのAPIを直接呼び出す場合は、先にログインしてセッションCookieを保持する。`python3`標準ライブラリで呼ぶ例:

```python
import http.cookiejar
import json
import urllib.request

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
login = urllib.request.Request(
    "http://localhost:8000/api/auth/login",
    data=json.dumps({"loginId": "yuki", "password": "caliboo-yuki"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
opener.open(login).close()
print(opener.open("http://localhost:8000/api/home/summary").read().decode("utf-8"))
```

!NOTE: テストは`pyproject.toml`の`addopts`により既定で`--disable-socket --allow-unix-socket`が付く(テストが実ネットワークへ出ないことを担保するため)。Unixソケットを許可しているのは、FastAPIの`TestClient`が内部のイベントループ起動に`socketpair`(AF_UNIX)を使うためで、これを塞ぐと`TestClient`を使うテストが起動できなくなる。

## 運用拡張API（2026-09-28）

以下の既存APIの変更と追加APIを使用する。正確な型定義は `schemas/agent_jobs.py`、`routers/users.py`、`routers/proposal_agent.py` と `/openapi.json` を参照。

- `login/me` は `streakDays` を返す。ログイン失敗が実接続元単位で15分20回に達した場合は429と `Retry-After`（秒）を返す。
- ホームの `strengths` は本人の承認済み候補（可変件数）。各要素は `label,tone,evidence,growthAction`。未承認のみなら空配列。
- OJTのmessagesは共通初期メッセージと本人×課の永続履歴、`escalated`を返す。chatは質問と一次回答を保存する。
- クイズの `choices` は文字列または `{text,imageUrl,alt}`。画像は `/quiz-assets/[A-Za-z0-9_-]+.svg` に限定、alt必須。`selectedIndex`が範囲外なら422。正解済み問題の重複を数えず、本人の分野別・資格全体進捗を更新する。画像自体は認証を要しない静的コンテンツ。
- 課題作成は任意の `targetUserId`（有効なmember）を受け付ける。不正な対象は404。フィードバックは任意の `score`（0〜100整数/null）を受け付け、提出の詳細にも返す。

| Method | Path | 権限・入出力 |
| --- | --- | --- |
| GET | /api/users | admin。`{users:[{id,loginId,displayName,role,active,departmentId,history}]}`。任意のdepartmentIdで絞込 |
| POST | /api/users | admin。loginId/displayName/password/role/departmentId。パスワード12〜128文字。作成201、ID重複409 |
| POST | /api/users/{user_id} | admin。displayName/role/active/departmentId、任意password。本人無効化・降格409。パスワード/ロール変更・無効化で既存セッション失効 |
| POST | /api/ojt/departments/{dept_id}/escalate | member本人。保存済み会話がある課を相談。重複依頼は冪等。発言なし409 |
| GET | /api/ojt/escalations | admin。任意departmentId。threadsとpendingCount。明示相談された履歴のみ |
| POST | /api/ojt/escalations/{thread_id}/reply | admin。`{text}`。同じ履歴に講師名付き回答を保存。未相談404、回答済み409 |
| GET | /api/development/strengths | 本人/講師。任意userId（他人指定はadminのみ）。candidatesとjobs。memberには承認済み候補のみ |
| POST | /api/development/strengths/{user_id}/request | admin。提出材料をスナップショット化。材料なし409、対象不在404。同じ材料は同じジョブ |
| GET | /api/development/jobs | admin。処理待ちjobs |
| GET | /api/development/strength-materials/schema | admin。強み解析入力 `StrengthAnalysisMaterials` のJSON Schema |
| GET | /api/development/jobs/{job_id} | admin。ジョブ情報・materials・result。強み材料はv1へ検証・整形。不正な保存済み材料/未対応版は409 |
| POST | /api/development/jobs/{job_id}/strength-result | admin。StrengthResultを取り込み候補を確認待ちで保存。引用/材料ID/skillCode重複を検証。古い/完了済み409、形式422 |
| POST | /api/development/strengths/{candidate_id}/decision | admin。`{status:approved/rejected,label,growthAction}`。確認待ちのみ。既決409 |
| GET | /api/development/evaluations/{job_id}/materials | admin。人間ラベル付け用のv1材料（解析結果を含めない）。不正な保存済み材料/未対応版は409 |
| POST | /api/development/evaluations/{job_id} | admin。`{skillCodes,accepted,comment}`。完了した強みジョブのみ。本人の評価を更新しmatch(exact/partial/none)を返す |
| GET | /api/development/evaluations | admin。evaluatedJobs/requiredJobs=20/requiredReviewers=2/agreement/acceptance/threshold=0.8/status。statusはinsufficient_data/passed/failed |
| POST | /api/assignment-proposals/{proposal_id}/regenerate | admin。`{instruction}`。確認待ち課題案に再生成ジョブを登録 |
| GET | /api/assignment-proposals/{proposal_id}/revisions | admin。調整指示とprevious（旧課題内容）の履歴 |
| POST | /api/assignment-proposals/agent-jobs/{job_id}/result | admin。ProposalAgentResultを保存。配信済み・見送り済み・旧版不一致409 |

強みジョブの `materials` は `{schemaVersion:"strength-materials.v1", sources:[...]}`。各sourceは `id,kind,field,text,date,sourceRole,evidenceEligible` を持つ。分類・上限・原文保持・旧ジョブ変換は [強み解析入力の仕様](strength-analysis-input.md) を参照。ジョブ作成、材料取得、結果取込に同じスキーマを適用する。結果取込時も不正な保存済み材料/未対応版は409。旧ジョブのDB内容を読み取り時に書き換えない。

StrengthResultの形:

```json
{
  "trace": {"provider":"codex_agent","model":"gpt-6-astra","promptVersion":"live-2026-09-28.2"},
  "candidates": [{"label":"確認する力","skillCode":"TEST","confidence":75,
    "evidence":[{"materialId":"report:1:keep","quote":"原文の引用"}],
    "growthAction":"次の小さな取り組み"}],
  "notes":"解析の根拠と限界"
}
```

候補は最大10件、根拠は候補ごとに1〜10件、confidenceは0〜100整数。ジョブのsourcesから原文を引用する。`evidenceEligible=false`（Problem/Try/気分コメント）を根拠にすると422。入力なしを推測して補完せず空候補を保存できる。traceはモデル・プロンプト版の追跡情報であり、サーバーがモデル実行を証明する署名ではない。取込は認証済み講師専用。

ProposalAgentResultはtrace/title/body/messageForMember/rationale/estimateMinutes（5〜480）。再生成結果の自動配信はしない。
