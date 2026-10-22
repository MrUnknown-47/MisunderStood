import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.routers import (
    health,
    sessions,
    interpretations,
    analysis,
    issues,
    agreements,
    bridge_test
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("misunderstood")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables are created
    logger.info("Initializing database tables...")
    init_db()
    logger.info("MISUNDERSTOOD backend started successfully.")
    yield
    # Shutdown
    logger.info("MISUNDERSTOOD backend shutting down.")


app = FastAPI(
    title="MISUNDERSTOOD API",
    description="Backend API for MISUNDERSTOOD — 'Same conversation. Different realities.'",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error_msg = errors[0].get("msg", "Invalid request payload.") if errors else "Validation error."
    first_field = ".".join(str(loc) for loc in errors[0].get("loc", [])) if errors else ""
    detail = f"{first_field}: {first_error_msg}" if first_field else first_error_msg
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
        content={"detail": detail}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."}
    )


# Include Routers
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(interpretations.router)
app.include_router(analysis.router)
app.include_router(issues.router)
app.include_router(agreements.router)
app.include_router(bridge_test.router)
