from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import analytics, auth, health, tickets
from app.db.database import Base, engine

if settings.environment.lower() != "production":
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Datastraw Operations CRM",
    version="1.0.0",
    description="Support CRM operations dashboard for Datastraw",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.on_event("startup")
async def validate_runtime_configuration() -> None:
    if settings.environment.lower() == "production" and settings.database_url.lower().startswith("sqlite"):
        raise RuntimeError("Production requires a persistent external DATABASE_URL; SQLite is not supported on Vercel.")


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
