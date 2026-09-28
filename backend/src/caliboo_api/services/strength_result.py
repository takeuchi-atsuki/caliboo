"""通常解析とホールドアウトで共通に用いるスキル・原文引用の検証。"""

from fastapi import HTTPException

from caliboo_api.schemas.agent_jobs import StrengthResult


def validate_evidence(payload: StrengthResult, materials: dict) -> dict:
    sources = {item["id"]: item for item in materials["sources"]}
    codes = [item.skillCode for item in payload.candidates]
    if len(codes) != len(set(codes)):
        raise HTTPException(422, "duplicate skill code")
    for candidate in payload.candidates:
        for evidence in candidate.evidence:
            source = sources.get(evidence.materialId)
            if (source is None or not source["evidenceEligible"]
                    or evidence.quote not in source["text"]):
                raise HTTPException(422, "evidence must quote an eligible source")
    return sources
