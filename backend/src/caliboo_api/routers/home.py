from fastapi import APIRouter, Depends

from caliboo_api.auth.deps import get_current_user
from caliboo_api.data.home_data import fetch_home_summary
from caliboo_api.models import User
from caliboo_api.schemas.home import HomeSummary

router = APIRouter(prefix="/api/home", tags=["home"])


@router.get("/summary", response_model=HomeSummary)
def get_home_summary(user: User = Depends(get_current_user)) -> HomeSummary:
    return fetch_home_summary(user.id)
