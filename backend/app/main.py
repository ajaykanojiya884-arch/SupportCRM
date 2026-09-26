import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import analytics, auth, health, tickets
from app.db.database import Base, engine


def is_production_runtime() -> bool:
    return settings.environment.lower() == "production" or os.getenv("VERCEL") == "1"


if not is_production_runtime():
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Datastraw Operations CRM",
    version="1.0.0",
    description="Support CRM operations dashboard for Datastraw",
    docs_url=None if is_production_runtime() else "/docs",
    redoc_url=None if is_production_runtime() else "/redoc",
    openapi_url=None if is_production_runtime() else "/openapi.json",
)


@app.on_event("startup")
async def validate_runtime_configuration() -> None:
    if not is_production_runtime():
        return

    if settings.database_url.lower().startswith("sqlite"):
        raise RuntimeError("Production requires a persistent external DATABASE_URL; SQLite is not supported on Vercel.")

    smtp_host = settings.smtp_host.strip().lower()
    if (
        not settings.smtp_user.strip()
        or not settings.smtp_password.strip()
        or not smtp_host
        or smtp_host in {"localhost", "127.0.0.1", "0.0.0.0"}
    ):
        raise RuntimeError("Production requires SMTP_HOST, SMTP_USER, and SMTP_PASSWORD for email verification.")

    if settings.debug:
        raise RuntimeError("DEBUG must be disabled in production.")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(tickets.router, prefix="/api", tags=["tickets"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])

@app.get("/")
async def root() -> dict:
    return {"message": "Datastraw Operations API"}
