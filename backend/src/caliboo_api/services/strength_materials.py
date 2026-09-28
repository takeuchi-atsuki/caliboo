"""保存済みスナップショットの検証と、版のない旧形式の互換変換。"""

from caliboo_api.schemas.strength_materials import (
    SCHEMA_VERSION,
    SOURCE_ROLES,
    StrengthAnalysisMaterials,
)


def normalize_strength_materials(materials: dict) -> dict:
    # !NOTE: 旧ジョブも保存時点の原文を使う。現在のDBから作り直すと根拠が変わる。
    if isinstance(materials, dict) and "schemaVersion" not in materials:
        materials = {**materials, "schemaVersion": SCHEMA_VERSION}
        sources = materials.get("sources")
        if isinstance(sources, list):
            materials["sources"] = [
                {
                    "sourceRole": (
                        SOURCE_ROLES.get(source.get("field"))
                        if isinstance(source.get("field"), str) else None
                    ),
                    **source,
                }
                if isinstance(source, dict) else source
                for source in sources
            ]
    return StrengthAnalysisMaterials.model_validate(materials).model_dump()
