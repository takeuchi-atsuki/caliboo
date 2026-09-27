"""FastAPIアプリ本体。

!NOTE: CORSミドルウェアは持たない。開発時はViteの`server.proxy`で`/api`をこのAPIへ
       転送し、画面とAPIを同一オリジンにするため(詳細は`docs/architecture.md`「認証・認可」)。

!NOTE: `auth.router`以外の全ルーターへ`Depends(get_current_user)`を一括付与している。
       ルーターを追加するたびに認証の付け忘れが起きないようにするため(各`APIRouter`側で
       個別に付与する方式だと、付け忘れたルーターのAPIが未認証のまま公開されてしまう)。
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI

from caliboo_api.auth.deps import get_current_user
from caliboo_api.config import get_settings
from caliboo_api.db import bootstrap_db, init_engine
from caliboo_api.routers import (
    assignment,
    assignment_proposal,
    auth,
    home,
    ojt,
    poc_strength,
    quiz,
    report,
    study,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_engine(settings.sqlite_path)
    bootstrap_db()
    yield


app = FastAPI(title="Caliboo API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(home.router, dependencies=[Depends(get_current_user)])
app.include_router(report.router, dependencies=[Depends(get_current_user)])
app.include_router(ojt.router, dependencies=[Depends(get_current_user)])
app.include_router(study.router, dependencies=[Depends(get_current_user)])
app.include_router(quiz.router, dependencies=[Depends(get_current_user)])
app.include_router(assignment.router, dependencies=[Depends(get_current_user)])
app.include_router(assignment_proposal.router, dependencies=[Depends(get_current_user)])
app.include_router(poc_strength.router, dependencies=[Depends(get_current_user)])
