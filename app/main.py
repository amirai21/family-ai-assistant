from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.database import init_db, close_db

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # initialize resources here (db, clients, caches)
    await init_db()
    yield
    # clean up resources here
    await close_db()

def create_app() -> FastAPI:
    app = FastAPI(
        title="Family AI Assistant API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    app.include_router(api_router, prefix="/api")

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {"message": "Family AI Assistant API"}

    return app

app = create_app()