from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_day2_schema() -> None:
    """Add Day 2 columns to a Day 1 database without introducing a migration framework."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = inspector.get_table_names()
        if "devices" not in tables:
            return
        columns = {column["name"] for column in inspector.get_columns("devices")}
        additions = {
            "agent_secret_hash": "VARCHAR(255)",
            "gateway_latency_ms": "DOUBLE PRECISION",
            "internet_latency_ms": "DOUBLE PRECISION",
            "packet_loss_pct": "DOUBLE PRECISION",
            "last_metrics_at": "TIMESTAMPTZ",
            "updated_at": "TIMESTAMPTZ",
        }
        for name, ddl in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE devices ADD COLUMN {name} {ddl}"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_devices_last_seen_at ON devices (last_seen_at)"))

