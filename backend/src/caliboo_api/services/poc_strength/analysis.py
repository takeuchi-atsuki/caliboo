"""ルールベースの3層強み解析エンジン(SFIA → CliftonStrengths → Will-Skill)。

!NOTE: 解析への入力は trajectory[](task.title/description・workerOutput・
       trainerFeedback)・diary・統合レビューのみに限定する。`injectedPersona`/
       `skillHint`は受け取らない(呼び出し側の`pipeline.py`が組み立てる時点で
       含めない)。答え(注入ペルソナ・タスクのSFIAヒント)を解析自身が読めると
       仕様書§8(a)の検証が自明に通ってしまい、パイプラインの健全性を測る
       独立した検査として機能しなくなるため(循環評価の回避、仕様書§8・§9)。
"""

from caliboo_api.services.text_utils import find_first_match, split_sentences

from . import skill_catalog as catalog

_SentenceSource = tuple[str, dict]


def _collect_trajectory_texts(trajectory: list[dict]) -> list[_SentenceSource]:
    """軌跡のテキストを、根拠としての強い順(本人の成果物 → 指導者の所見 → 課題文)に並べる。

    !NOTE: `_find_evidence()`は先頭から最初に一致した文を引用するため、この並び順が
           そのまま「どの文を根拠として提示するか」の優先順位になる。課題文(task)は
           本人が示した振る舞いではなく与えられたお題であり、根拠としては最も弱いので
           最後に置く(他に一致が無い場合のみ引用される)。
    """
    def source(iteration: int, field: str) -> dict:
        return {"kind": "trajectory", "iteration": iteration, "field": field}

    worker_texts: list[_SentenceSource] = []
    trainer_texts: list[_SentenceSource] = []
    task_texts: list[_SentenceSource] = []
    for item in trajectory:
        iteration = item["iteration"]
        task = item["task"]
        worker_texts.append((item["workerOutput"], source(iteration, "workerOutput")))
        trainer_texts.append((item["trainerFeedback"], source(iteration, "trainerFeedback")))
        task_texts.append((task["title"], source(iteration, "task.title")))
        task_texts.append((task["description"], source(iteration, "task.description")))
    return worker_texts + trainer_texts + task_texts


def _collect_diary_texts(diary: dict) -> list[_SentenceSource]:
    """日報から根拠テキストを集める。

    !NOTE: `mentorComment`は意図的に含めない。中身はFan-inが束ねた3職種レビューの全文で、
           レビュー種別の根拠としてすでに数えているため、含めると同じ文章を「日報でも
           裏付けられた」と二重計上し、暫定(0.6)が軒並み確定(0.85)に繰り上がってしまう。
    """

    def source(field: str) -> dict:
        return {"kind": "diary", "field": field}

    texts: list[_SentenceSource] = []
    for index, task in enumerate(diary["tasks"]):
        texts.append((task["what"], source(f"tasks[{index}].what")))
        texts.append((task["progressDesc"], source(f"tasks[{index}].progressDesc")))
    feelings = diary["feelings"]
    texts.append((feelings["trigger"], source("feelings.trigger")))
    texts.append((feelings["nextAction"], source("feelings.nextAction")))
    kpt = diary["kpt"]
    texts.append((kpt["keep"], source("kpt.keep")))
    texts.append((kpt["problem"], source("kpt.problem")))
    texts.append((kpt["try"], source("kpt.try")))
    return texts


def _collect_review_texts(reviews: list[dict]) -> list[_SentenceSource]:
    return [
        (
            review["comment"],
            {"kind": "review", "field": "comment", "role": review["agentKey"]},
        )
        for review in reviews
    ]


def _find_evidence(texts: list[_SentenceSource], keywords: tuple[str, ...]) -> dict | None:
    for text, source in texts:
        match = find_first_match(split_sentences(text), keywords)
        if match:
            return {"quote": match, "source": source}
    return None


def _keyword_hit_count(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _learning_agility(trajectory: list[dict], keywords: tuple[str, ...]) -> tuple[dict, bool]:
    """フィードバックを踏まえた伸びを、その強みが実際に現れた周回間でのみ測る。

    戻り値は`(learning_agility, sustained)`。`sustained`は「複数の周回にわたって
    継続的に観測できたか」を表し、Will軸の判定に使う。

    !NOTE: 全周回のキーワード出現数を単純比較すると、後半の周でタスクの対象が
           別スキルへ移っただけで「衰退」と誤判定してしまう(タスクが変われば
           そのスキルへの言及が無くなるのは当然のため)。そこで、そのスキルへの
           言及が実際にあった周回(`active_indices`)だけを比較対象にする。
    """
    counts = [_keyword_hit_count(item["workerOutput"], keywords) for item in trajectory]
    active_indices = [index for index, count in enumerate(counts) if count > 0]
    if len(active_indices) < 2:
        return {"delta": "0", "note": "継続して観測できる周回が不足しているため成長は評価できない"}, False

    first_index, last_index = active_indices[0], active_indices[-1]
    delta_value = counts[last_index] - counts[first_index]
    delta = "+" if delta_value > 0 else ("-" if delta_value < 0 else "0")

    if delta_value > 0:
        note = f"{first_index + 1}周目から{last_index + 1}周目にかけて、言及が増えた"
    elif delta_value < 0:
        note = f"{first_index + 1}周目から{last_index + 1}周目にかけて、言及が減った"
    else:
        note = f"{first_index + 1}周目から{last_index + 1}周目にかけて、安定して現れている"

    return {"delta": delta, "note": note}, True


def _quadrant_and_policy(level: int, delta: str, sustained: bool) -> dict:
    """Will軸・Skill軸の2値からWill-Skill象限を決める。

    !NOTE: Will軸には確信度(＝その強みが在ると言える確からしさ)を使わない。
           確からしさは「意欲の高さ」ではないため、流用すると根拠の薄い強みが
           自動的に「意欲は高いが技能が低い」と断定されてしまう。仕様書§5が
           「learning agilityをWill側の主要シグナルとして扱う」としている通り、
           周回間の伸び(delta)と、複数周にわたる継続性(sustained)から判定する。
    """
    will_high = delta == "+" or (delta == "0" and sustained)
    skill_high = level >= catalog.LEVEL_WHEN_FULLY_SUPPORTED
    if will_high and skill_high:
        quadrant = "High Will / High Skill"
    elif will_high and not skill_high:
        quadrant = "High Will / Low Skill"
    elif not will_high and skill_high:
        quadrant = "Low Will / High Skill"
    else:
        quadrant = "Low Will / Low Skill"
    return {"quadrant": quadrant, "policy": catalog.QUADRANT_POLICY[quadrant]}


# 全体判定ごとの補足文。overallStatusと別々に組み立てると、
# 「一部は根拠不足(partial)」なのに「全て根拠が揃った」と書かれる等の食い違いが起きるため、
# 判定から一意に引く。
_NOTES_BY_OVERALL_STATUS = {
    "complete": "全ての強みについて十分な根拠が確認できた",
    "partial": "根拠が揃わない領域は暫定・評価保留とした",
    "insufficient": "根拠が不足するため、断定できる強みは無いと判断した",
}


def _overall_status(strengths: list[dict]) -> str:
    """全体判定。全件確定なら`complete`、断定できたものが1件も無ければ`insufficient`。"""
    if not strengths:
        return "insufficient"
    if all(item["status"] == "confirmed" for item in strengths):
        return "complete"
    if all(item["status"] == "insufficient_evidence" for item in strengths):
        return "insufficient"
    return "partial"


def analyze(
    *,
    subject_id: str,
    run_id: str,
    trajectory: list[dict],
    diary: dict,
    reviews: list[dict],
    generated_at: str,
    provider_name: str,
) -> dict:
    """trajectory・diary・レビューから Strength JSON を組み立てる。"""
    trajectory_texts = _collect_trajectory_texts(trajectory)
    diary_texts = _collect_diary_texts(diary)
    review_texts = _collect_review_texts(reviews)

    strengths = []
    for skill in catalog.SKILL_CATALOG:
        evidence_by_kind = {
            "trajectory": _find_evidence(trajectory_texts, skill.keywords),
            "diary": _find_evidence(diary_texts, skill.keywords),
            "review": _find_evidence(review_texts, skill.keywords),
        }
        support_count = sum(1 for evidence in evidence_by_kind.values() if evidence is not None)
        if support_count == 0:
            continue

        confidence = catalog.CONFIDENCE_BY_SUPPORT_COUNT[support_count]
        if confidence >= catalog.CONFIRMED_THRESHOLD:
            status = "confirmed"
        elif confidence >= catalog.TENTATIVE_THRESHOLD:
            status = "tentative"
        else:
            status = "insufficient_evidence"

        level = (
            catalog.LEVEL_WHEN_FULLY_SUPPORTED
            if support_count == len(catalog.SUPPORT_KINDS)
            else catalog.LEVEL_WHEN_PARTIALLY_SUPPORTED
        )
        learning, sustained = _learning_agility(trajectory, skill.keywords)

        # 根拠が足りない強み、およびWill軸を評価できなかった強みには、
        # 象限も育成アクションも付けない。
        #
        # !NOTE: 「評価できない」を「Willが低い」に変換しないための分岐。
        #        複数周にわたる観測が無いのに象限を出すと、単に観測機会が無かった
        #        だけの強みが「意欲が低い」と断定され、そこから育成アクション
        #        (短時間で終わる課題から始める等)まで出てしまう。根拠が無いものを
        #        断定しないという仕様書§9の方針は、確信度だけでなくWill軸にも及ぶ。
        held_back = status == "insufficient_evidence" or not sustained

        strengths.append(
            {
                "id": f"st_{skill.code.lower()}",
                "layerTask": {
                    "framework": "SFIA",
                    "skillCode": skill.code,
                    "skillName": skill.name,
                    "level": level,
                },
                "layerBehavior": {
                    "framework": "CliftonStrengths",
                    "themes": list(skill.themes),
                },
                "layerWillSkill": (
                    None if held_back else _quadrant_and_policy(level, learning["delta"], sustained)
                ),
                "confidence": confidence,
                "status": status,
                "evidence": [
                    {"quote": evidence["quote"], "source": evidence["source"]}
                    for evidence in evidence_by_kind.values()
                    if evidence is not None
                ],
                "learningAgility": learning,
                "growthContent": None if held_back else catalog.GROWTH_CONTENT_BY_SKILL[skill.code],
            }
        )

    overall_status = _overall_status(strengths)
    notes = _NOTES_BY_OVERALL_STATUS[overall_status]

    return {
        "subjectId": subject_id,
        "runId": run_id,
        "generatedAt": generated_at,
        "provider": provider_name,
        "strengths": strengths,
        "overallStatus": overall_status,
        "notes": notes,
    }
