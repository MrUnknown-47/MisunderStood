from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import init_db
from backend.app.routes.agreements import router as agreements_router
from backend.app.routes.issues import router as issues_router
from backend.app.routes.sessions import router as sessions_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Same conversation. Different realities. AI-powered misunderstanding detection.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router, prefix=settings.API_PREFIX)
app.include_router(issues_router, prefix=settings.API_PREFIX)
app.include_router(agreements_router, prefix=settings.API_PREFIX)


@app.get("/api/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


dist_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="frontend")
