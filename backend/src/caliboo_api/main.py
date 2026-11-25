"""FastAPIアプリ本体。

!NOTE: CORSミドルウェアは持たない。開発時はViteの`server.proxy`で`/api`をこのAPIへ
       転送し、画面とAPIを同一オリジンにするため(詳細は`docs/architecture.md`「認証・認可」)。

!NOTE: `auth.router`以外の全ルーターへ`Depends(get_current_user)`を一括付与している。
       ルーターを追加するたびに認証の付け忘れが起きないようにするため(各`APIRouter`側で
       個別に付与する方式だと、付け忘れたルーターのAPIが未認証のまま公開されてしまう)。
"""

from contextlib import asynccontextmanager
import asyncio
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, InterfaceError

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
    users,
    development,
    proposal_agent,
    learning_actions,
    holdout,
)
from caliboo_api.services import ai_worker, llm


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_engine(settings.sqlite_path)
    bootstrap_db()
    stop = asyncio.Event()
    task = None
    if llm.provider_name() == "openai":
        task = asyncio.create_task(ai_worker.run_worker(stop, llm.settings()))
    try:
        yield
    finally:
        stop.set()
        if task is not None:
            await task


async def database_unavailable(_request: Request, _exc: Exception) -> JSONResponse:
    # !NOTE: DBエラーの詳細やSQLパラメーターをレスポンスに含めない。
    return JSONResponse(status_code=503, content={"detail": "database unavailable"})


def create_app(lifespan_handler=lifespan, *, include_docs: bool = True) -> FastAPI:
    """通常運用と限定試用で同じ認証・業務ルーターを構成する。"""
    app = FastAPI(
        title="Caliboo API", lifespan=lifespan_handler,
        docs_url="/docs" if include_docs else None,
        redoc_url="/redoc" if include_docs else None,
        openapi_url="/openapi.json" if include_docs else None,
    )
    if not include_docs:
        app.add_exception_handler(OperationalError, database_unavailable)
        app.add_exception_handler(InterfaceError, database_unavailable)

    app.include_router(auth.router)
    for router in (
        home, report, ojt, study, quiz, assignment, assignment_proposal, poc_strength,
        users, development, proposal_agent, learning_actions, holdout,
    ):
        app.include_router(router.router, dependencies=[Depends(get_current_user)])

    app.mount("/quiz-assets", StaticFiles(directory=Path(__file__).parent / "quiz_assets"),
              name="quiz-assets")
    return app


app = create_app()
