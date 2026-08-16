from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine
from app.core.redis import get_redis

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    database = "healthy"
    redis_status = "healthy"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database = "unavailable"

    try:
        get_redis().ping()
    except Exception:
        redis_status = "unavailable"

    overall = "healthy" if database == "healthy" and redis_status == "healthy" else "degraded"

    return {
        "status": overall,
        "services": {
            "api": "healthy",
            "database": database,
            "redis": redis_status,
        },
    }
