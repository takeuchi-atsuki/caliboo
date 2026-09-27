---
name: caliboo-strength-run
description: "強み解析PoC(`example/Caliboo_強み解析_PoC_機能追加_基本仕様書.md`)のrunを、事前執筆の台本ではなく本セッションのClaudeが4種のエージェント(strength-worker/-trainer/-reviewer/-analyst)を演じて実行し、`POST /api/poc/runs/import`へ投入する。"
when_to_use: "強み解析PoCを実LLMで(台本のデモシナリオ以外で)動かしたいとき、検証(a)機構妥当性を確認したいとき、既存3ペルソナ以外のシナリオで`/strengths`画面の表示を確認したいときに使う。"
---

強み解析PoCの①ループ×3 → ②日報 → ③3職種レビュー(Fan-inはサーバー側) → ④解析、を本セッションのClaudeが演じて1 run分の入力を組み立て、`POST /api/poc/runs/import`へ投入する。

前提として`docs/architecture.md`「強み解析PoCの構成」節が説明する通り、アプリ実行時にLLMを呼ぶ経路は無い(台本ベースの`AuthoredMockProvider`のみ)。本skillはその制約の外側、つまり「Claude Codeセッション自身が生成を担い、結果を投入する」経路を担う。

## 前提条件

- backend devサーバーが`http://localhost:8000`で起動していること(`./devel/dev-server.sh`、または`cd backend && python3 -m uvicorn caliboo_api.main:app --reload --port 8000`)。起動していなければユーザーに起動を依頼するか、Bashでバックグラウンド起動する。
- 4つのAgent定義(`.claude/agents/strength-worker.md`・`strength-trainer.md`・`strength-reviewer.md`・`strength-analyst.md`)が使える状態であること。

## 1. 入力の確認

次が未指定ならAskUserQuestionで確認する。

| 項目 | 説明 | 既定 |
| --- | --- | --- |
| `subjectId` | 対象者ID | `emp_101`(デモ台本の`emp_001`〜`003`と衝突しない値にする) |
| `label` | 実行履歴に表示する名前 | ユーザー入力必須 |
| 初期タスク(1周目) | `title`・`description`・`skillHint`(任意、SFIAコード) | ユーザー入力必須 |
| `injectedPersona` | 検証(a)用。既知の強みを注入する場合のみ | 省略可(`null`) |
| `mode` | `agent`(本案・自走)または`hitl`(別案・人間が周ごとに承認/上書き) | `agent` |

## 2. 3周ループ

各周(iteration=1,2,3)ごとに、スクラッチパッドの`run.json`へ追記しながら進める。

1. `strength-worker`を反復モードで起動する(`run_in_background: false`。次周が前周の結果に依存するため直列実行)。入力: ペルソナ説明(`injectedPersona`があれば含める)・当該周のタスク定義・それまでの全trajectory。
2. `strength-trainer`を起動する。入力: 当該周のタスク定義・`workerOutput`・それまでのtrajectory。1〜2周目は`nextTask`も受け取る。
3. `mode: hitl`の場合、`trainerFeedback`をAskUserQuestionで提示し「承認する/上書きする」を選ばせる。上書きされた内容を`humanOverride`に記録する(`mode: agent`では`humanOverride`は常に`null`)。
4. `trajectory[]`に`{iteration, task, workerOutput, trainerFeedback, humanOverride}`を追記する。
5. 1〜2周目は、`strength-trainer`が返した`nextTask`を次周のタスク定義として使う(3周目には次タスクが無い)。

## 3. 日報の集約

`strength-worker`を日報モードで1回起動する。入力: 3周分の全trajectory。出力をそのまま`diary`とする(`mentorComment`は含まれない。サーバー側がFan-in結果で補完する)。

## 4. 3職種レビュー

`strength-reviewer`を`alpha`(管理職/MELCHIOR)・`beta`(講師/BALTHASAR)・`gamma`(シニアエンジニア/CASPER)の3ロールで並列起動する(3つのAgent呼び出しを同一メッセージ内で行う。前後の依存が無いため)。各ロールには`diary`のみを渡す(trajectoryは渡さない。基本仕様書§3の入力欄に合わせる)。返ってきた`comment`・`flags`に`agentKey`・`reviewerRole`・`magiTone`を補って`reviews[]`(3件、alpha→beta→gammaの順)を組み立てる。

## 5. 独立解析(別モデル)

`strength-analyst`を起動する。入力は次のように整形する(いずれも仕様書§8(a)の循環評価回避のため必須の加工):

- `trajectory`から`task.skillHint`を取り除いたコピーを渡す
- `injectedPersona`は渡さない
- `diary`は`mentorComment`が無い状態(手順3の出力そのもの)を渡す
- `reviews`は手順4で組み立てた3件(Fan-in前の個別コメント)を渡す

返ってきた`strengths`/`overallStatus`/`notes`に、`subjectId`・`runId`(空文字のままでよい。サーバー側が投入後に補完する対象は`strengths`側のみで、`externalAnalysis`側は補完されない)・`generatedAt`(現在時刻のISO8601)・`provider`(例: `"strength-analyst_opus_2026-09-24.1"`、モデル名とpromptVersionを含める)を補い、`externalStrengths`として保持する。

## 6. サーバーへの投入

`POST /api/poc/runs/import`のリクエストボディを組み立てる。

```json
{
  "personaKey": "external_claude",
  "subjectId": "<手順1>",
  "label": "<手順1>",
  "injectedPersona": "<手順1、省略時null>",
  "trajectory": "<手順2で組み立てた3件>",
  "diary": "<手順3>",
  "reviews": "<手順4>",
  "trace": {
    "generationProvider": "claude_session",
    "agents": [
      { "key": "strength-worker", "model": "sonnet", "promptVersion": "2026-09-24.1" },
      { "key": "strength-trainer", "model": "sonnet", "promptVersion": "2026-09-24.1" },
      { "key": "strength-reviewer", "model": "sonnet", "promptVersion": "2026-09-24.1" },
      { "key": "strength-analyst", "model": "opus", "promptVersion": "2026-09-24.1" }
    ]
  },
  "externalStrengths": "<手順5>"
}
```

`model`・`promptVersion`は実際に使用したAgent定義のfrontmatter(`model`)と本文冒頭の`promptVersion`をそのまま転記する(定義を改訂したら値も更新する)。

### HTTP呼び出し方法

`curl`/`wget`は`.claude/settings.json`のdenyで禁止されているため使わない。スクラッチパッドへペイロードをJSONファイルとして書き出し、`python3`標準ライブラリ(`urllib.request`)でPOSTする。

APIは`/api/auth/login`・`/api/auth/logout`以外すべて認証必須のため、開発用の講師アカウント(`sensei`、`docs/screens/login.md`参照)でログインし、発行されたセッションCookieを付けて投入する。

> [!NOTE]
> 投入経路だけを認証の対象外にしなかったのは、誰でもrunを投入できる穴を残さないため(ユーザー判断、2026-09-25)。

1. Writeツールでスクラッチパッドに`payload.json`を書く。
2. 次のPythonスクリプトを同ディレクトリに`post_import.py`として保存し、Bashで`python3 post_import.py`を実行する。

```python
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"

opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
)


def post_json(path, body):
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return opener.open(request, timeout=30)


with open("payload.json", encoding="utf-8") as f:
    payload = json.load(f)

try:
    post_json("/api/auth/login", {"loginId": "sensei", "password": "caliboo-sensei"}).close()
    with post_json("/api/poc/runs/import", payload) as response:
        print(response.status)
        print(response.read().decode("utf-8"))
except urllib.error.HTTPError as error:
    print(error.code, file=sys.stderr)
    print(error.read().decode("utf-8"), file=sys.stderr)
    sys.exit(1)
```

ログインで401が返った場合は、DBが旧スキーマのまま、またはシードのアカウントが変更されている可能性がある(`docs/screens/login.md`参照)。

422(バリデーションエラー)が返った場合は、レスポンス本文のエラー内容を確認し、`trajectory`の周回連番・`reviews`の3ロール過不足・`diary.tasks`の空配列などを見直して再投入する(`docs/api.md`「POST /api/poc/runs/import」参照)。

## 7. 突き合わせと報告

投入結果(`runId`・ルールベース解析`strengths`)と、手順5で送った`externalStrengths`(レスポンスの`trace.externalAnalysis`に格納されている)を突き合わせ、表で提示する。

| skillCode | ルールベース(status/confidence) | strength-analyst(status/confidence) | 一致 |
| --- | --- | --- | --- |
| ... | ... | ... | ✅/❌ |

`injectedPersona`を注入した実行(検証(a))では、注入した強みが両方の解析で`confirmed`相当として復元できているかを明示する。復元できていない場合は、パイプラインの不具合かエージェント出力の内容不足かを切り分けて報告する。

## 8. 画面での確認案内

`http://localhost:5173/strengths`を開き、実行履歴から今回の`runId`を選ぶと結果が確認できる旨を案内する(`docs/screens/strengths.md`参照。デモシナリオ選択の一覧には出ない)。

## トレーサビリティ

各エージェント呼び出しの入出力(手順2〜5)は、スクラッチパッドに`iteration_1_worker.json`のような形で個別に保存しておく。基本仕様書§6が求めるトレーサビリティを、投入後もセッション内で追跡できるようにするため。
