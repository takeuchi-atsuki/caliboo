from fastapi import APIRouter, HTTPException

from caliboo_api.data.poc_strength_data import (
    create_imported_run,
    create_run,
    fetch_run_list,
    get_run_detail,
    list_persona_options,
)
from caliboo_api.schemas.poc_strength import (
    PocDiary,
    PocPersonaListResponse,
    PocReviewsBundle,
    PocRunCreateRequest,
    PocRunDetail,
    PocRunImportRequest,
    PocRunListResponse,
    StrengthOutput,
)
from caliboo_api.services.poc_strength.pipeline import UnknownPersonaError

router = APIRouter(prefix="/api/poc", tags=["poc_strength"])


def _get_detail_or_404(run_id: str) -> dict:
    detail = get_run_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    return detail


@router.get("/personas", response_model=PocPersonaListResponse)
def list_personas() -> PocPersonaListResponse:
    return PocPersonaListResponse(personas=list_persona_options())


@router.post("/runs", response_model=PocRunDetail)
def create_new_run(payload: PocRunCreateRequest) -> PocRunDetail:
    try:
        return create_run(payload.personaKey)
    except UnknownPersonaError:
        raise HTTPException(status_code=404, detail=f"persona not found: {payload.personaKey}")


@router.post("/runs/import", response_model=PocRunDetail)
def import_run(payload: PocRunImportRequest) -> PocRunDetail:
    """外部(Claude Codeセッション等)で生成したrun一式を受け取り、Fan-in統合・解析・
    永続化を行う。バリデーション(trajectoryの3周連番・reviewsの3職種過不足)は
    `PocRunImportRequest`側で行い、違反時は422になる。
    """
    return create_imported_run(payload.model_dump(by_alias=True))


@router.get("/runs", response_model=PocRunListResponse)
def list_runs() -> PocRunListResponse:
    return PocRunListResponse(runs=fetch_run_list())


@router.get("/runs/{run_id}", response_model=PocRunDetail)
def get_run(run_id: str) -> PocRunDetail:
    return _get_detail_or_404(run_id)


@router.get("/runs/{run_id}/diary", response_model=PocDiary)
def get_run_diary(run_id: str) -> PocDiary:
    return _get_detail_or_404(run_id)["diary"]


@router.get("/runs/{run_id}/reviews", response_model=PocReviewsBundle)
def get_run_reviews(run_id: str) -> PocReviewsBundle:
    return _get_detail_or_404(run_id)["reviews"]


@router.get("/runs/{run_id}/strengths", response_model=StrengthOutput)
def get_run_strengths(run_id: str) -> StrengthOutput:
    return _get_detail_or_404(run_id)["strengths"]
