from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health, prompt, shopping
from app.config import get_settings
from app.database.database import init_db
from app.store.routes import router as store_router
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="CartMind", description="Autonomous AI shopping agent", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url, "http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(shopping.router)
    app.include_router(chat.router)
    app.include_router(prompt.router)
    app.include_router(store_router)
    return app


app = create_app()
