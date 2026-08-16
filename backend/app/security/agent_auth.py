from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.models.device import Device
from app.security.passwords import verify_secret


def get_agent_device(
    device: Device,
    db: Session,
    agent_secret: str | None,
) -> Device:
    if not agent_secret or not verify_secret(agent_secret, device.agent_secret_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent credentials",
        )
    return device


def require_agent_secret(
    device: Device,
    db: Session,
    x_agent_secret: str | None,
) -> Device:
    return get_agent_device(device, db, x_agent_secret)
