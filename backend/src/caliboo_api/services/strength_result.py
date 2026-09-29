"""通常解析とホールドアウトで共通に用いるスキル・原文引用の検証。"""

from fastapi import HTTPException

from caliboo_api.schemas.agent_jobs import StrengthResult


def validate_evidence(payload: StrengthResult, materials: dict) -> dict:
    sources = {item["id"]: item for item in materials["sources"]}
    codes = [(item.kind, item.skillCode) for item in payload.candidates]
    if len(codes) != len(set(codes)):
        raise HTTPException(422, "duplicate kind and skill code")
    for candidate in payload.candidates:
        self_records = set()
        for evidence in candidate.evidence:
            source = sources.get(evidence.materialId)
            if (source is None or not source["evidenceEligible"]
                    or evidence.quote not in source["text"]):
                raise HTTPException(422, "evidence must quote an eligible source")
            if source["sourceRole"] in {"self_report", "work_product"}:
                # !NOTE: 同じ提出の回答と所見は、二度の本人観測とは数えない。
                self_records.add((source["kind"], source["id"].split(":")[1]))
        if candidate.kind == "work_style" and len(self_records) < 2:
            raise HTTPException(422, "work style requires two distinct self records")
    return sources
