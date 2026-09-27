"""強み解析PoCのDBアクセス層。"""

import re
from datetime import datetime, timezone

from caliboo_api.db import session_scope
from caliboo_api.models import PocRun
from caliboo_api.services.poc_strength import pipeline

_RUN_ID_PREFIX = "run_"
_RUN_ID_PATTERN = re.compile(r"^run_(\d+)$")


def _format_run_id(row_id: int) -> str:
    return f"{_RUN_ID_PREFIX}{row_id:04d}"


def _parse_run_id(run_id: str) -> int | None:
    """`run_id`を行IDへ変換する。

    !NOTE: `_format_run_id()`が生成する正規形式(`run_0001`)と完全一致するものだけを
           受理する(先頭ゼロの桁数違い等で往復一致しない文字列は拒否する)。`run_1`や
           `run_00001`のような非正規形式も緩く受理すると、同一リソースを指す複数の
           URLが並立してしまう。`docs/api.md`が明記する「不正な形式のIDは404」を
           実装と一致させるため、往復一致で正規形式のみ受理する。
    """
    match = _RUN_ID_PATTERN.match(run_id)
    if match is None:
        return None
    row_id = int(match.group(1))
    if _format_run_id(row_id) != run_id:
        return None
    return row_id


def _to_summary(row: PocRun) -> dict:
    return {
        "id": _format_run_id(row.id),
        "personaKey": row.persona_key,
        "subjectId": row.subject_id,
        "label": row.label,
        "injectedPersona": row.injected_persona,
        "status": "completed",
        "createdAt": row.created_at,
    }


def _to_detail(row: PocRun) -> dict:
    return {
        **_to_summary(row),
        "trajectory": row.trajectory,
        "diary": row.diary,
        "reviews": row.reviews,
        "strengths": row.strengths,
        "trace": row.trace,
    }


def list_persona_options() -> list[dict]:
    return pipeline.list_personas()


def _persist_run(result: dict) -> dict:
    """パイプラインが組み立てたrun一式を1件永続化し、詳細を返す。

    パイプラインは実行時点ではrun_idを知らない(DB採番前のため)。挿入してIDが
    確定してから`strengths.runId`を補完し、それを含めて保存する。
    `create_run()`(台本経由)・`create_imported_run()`(外部投入経由)で共用する。
    """
    with session_scope() as session:
        row = PocRun(
            persona_key=result["personaKey"],
            subject_id=result["subjectId"],
            label=result["label"],
            injected_persona=result["injectedPersona"],
            trajectory=result["trajectory"],
            diary=result["diary"],
            reviews=result["reviews"],
            strengths=result["strengths"],
            trace=result["trace"],
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        session.add(row)
        session.flush()

        row.strengths = {**row.strengths, "runId": _format_run_id(row.id)}
        session.commit()
        session.refresh(row)
        return _to_detail(row)


def create_run(persona_key: str) -> dict:
    """ペルソナキーからパイプラインを同期実行し、runを1件永続化して詳細を返す。"""
    return _persist_run(pipeline.run_pipeline(persona_key))


def create_imported_run(payload: dict) -> dict:
    """外部(Claude Codeセッション等)で生成したrun一式を1件永続化して詳細を返す。

    `pipeline.import_run()`がFan-in統合・解析を行った結果をそのまま保存する点は
    `create_run()`と同じで、runの組み立て元(台本 or 外部投入)だけが異なる。
    """
    return _persist_run(pipeline.import_run(payload))


def fetch_run_list() -> list[dict]:
    """run一覧を作成順の新しい方から返す。"""
    with session_scope() as session:
        rows = session.query(PocRun).order_by(PocRun.id.desc()).all()
        return [_to_summary(row) for row in rows]


def get_run_detail(run_id: str) -> dict | None:
    row_id = _parse_run_id(run_id)
    if row_id is None:
        return None

    with session_scope() as session:
        row = session.get(PocRun, row_id)
        if row is None:
            return None
        return _to_detail(row)
