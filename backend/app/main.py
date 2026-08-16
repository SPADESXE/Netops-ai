from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.devices import router as devices_router
from app.api.routes.health import router as health_router
from app.core.database import Base, engine, ensure_day2_schema
from app.models import Device, NetworkInterface, Organization, User  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_day2_schema()
    yield


app = FastAPI(
    title="NetOpsAI API",
    version="0.2.0",
    description="AI-powered Network Operations SaaS API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(devices_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "name": "NetOpsAI API",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
    }
