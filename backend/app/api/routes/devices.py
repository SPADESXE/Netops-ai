import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.device_status import is_device_online
from app.models.device import Device
from app.models.network_interface import NetworkInterface
from app.models.user import User
from app.schemas.devices import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceResponse,
    HeartbeatRequest,
    InterfaceResponse,
    MetricsRequest,
)
from app.security.auth import get_current_user
from app.security.passwords import hash_secret, verify_secret

router = APIRouter(prefix="/devices", tags=["devices"])


def _ensure_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")


def _get_tenant_device(db: Session, device_id: UUID, organization_id: UUID) -> Device:
    stmt = (
        select(Device)
        .options(selectinload(Device.interfaces))
        .where(Device.id == device_id, Device.organization_id == organization_id)
    )
    device = db.scalar(stmt)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


def _get_any_device(db: Session, device_id: UUID) -> Device:
    device = db.scalar(select(Device).options(selectinload(Device.interfaces)).where(Device.id == device_id))
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


def _response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        hostname=device.hostname,
        username=device.username,
        os_name=device.os_name,
        os_version=device.os_version,
        agent_version=device.agent_version,
        last_seen_at=device.last_seen_at,
        online=is_device_online(device.last_seen_at, settings.agent_heartbeat_timeout_seconds),
        gateway_latency_ms=device.gateway_latency_ms,
        internet_latency_ms=device.internet_latency_ms,
        packet_loss_pct=device.packet_loss_pct,
        interfaces=[
            InterfaceResponse(
                id=iface.id,
                name=iface.name,
                mac_address=iface.mac_address,
                ipv4_address=iface.ipv4_address,
                gateway=iface.gateway,
                dns_servers=[v for v in (iface.dns_server or "").split(",") if v],
                is_primary=iface.is_primary,
            )
            for iface in device.interfaces
        ],
    )


@router.post("/register", response_model=DeviceRegisterResponse, status_code=201)
def register_device(
    payload: DeviceRegisterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeviceRegisterResponse:
    _ensure_admin(user)

    existing = db.scalar(
        select(Device).where(
            Device.organization_id == user.organization_id,
            Device.hostname == payload.hostname,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="A device with this hostname already exists")

    agent_secret = secrets.token_urlsafe(32)
    device = Device(
        organization_id=user.organization_id,
        hostname=payload.hostname,
        username=payload.username,
        os_name=payload.os_name,
        os_version=payload.os_version,
        agent_version=payload.agent_version,
        agent_secret_hash=hash_secret(agent_secret),
        last_seen_at=datetime.now(timezone.utc),
    )

    for index, iface in enumerate(payload.interfaces):
        device.interfaces.append(
            NetworkInterface(
                name=iface.name,
                mac_address=iface.mac_address,
                ipv4_address=iface.ipv4_address,
                gateway=iface.gateway,
                dns_server=",".join(iface.dns_servers),
                is_primary=iface.is_primary or (index == 0 and len(payload.interfaces) == 1),
            )
        )

    db.add(device)
    db.commit()
    db.refresh(device)
    return DeviceRegisterResponse(
        device_id=device.id,
        agent_secret=agent_secret,
        message="Store this secret securely. It is shown only once.",
    )


def _authenticate_agent(db: Session, device_id: UUID, secret: str | None) -> Device:
    device = _get_any_device(db, device_id)
    if not secret or not device.agent_secret_hash or not verify_secret(secret, device.agent_secret_hash):
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    return device


@router.post("/{device_id}/heartbeat")
def heartbeat(
    device_id: UUID,
    payload: HeartbeatRequest,
    x_agent_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = _authenticate_agent(db, device_id, x_agent_secret)
    now = datetime.now(timezone.utc)
    device.last_seen_at = now

    if payload.interface_name:
        iface = db.scalar(
            select(NetworkInterface).where(
                NetworkInterface.device_id == device.id,
                NetworkInterface.name == payload.interface_name,
            )
        )
        if iface and payload.ip_address:
            iface.ipv4_address = payload.ip_address
            iface.updated_at = now
    db.commit()
    return {"device_id": device.id, "last_heartbeat_at": now, "online": True}


@router.post("/{device_id}/metrics")
def metrics(
    device_id: UUID,
    payload: MetricsRequest,
    x_agent_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = _authenticate_agent(db, device_id, x_agent_secret)
    now = datetime.now(timezone.utc)
    device.gateway_latency_ms = payload.gateway_latency_ms
    device.internet_latency_ms = payload.internet_latency_ms
    device.packet_loss_pct = payload.packet_loss_pct
    device.last_metrics_at = now
    device.last_seen_at = device.last_seen_at or now
    db.commit()
    return {
        "device_id": device.id,
        "gateway_latency_ms": device.gateway_latency_ms,
        "internet_latency_ms": device.internet_latency_ms,
        "packet_loss_pct": device.packet_loss_pct,
        "recorded_at": now,
    }


@router.get("", response_model=list[DeviceResponse])
def list_devices(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DeviceResponse]:
    _ensure_admin(user)
    devices = db.scalars(
        select(Device)
        .options(selectinload(Device.interfaces))
        .where(Device.organization_id == user.organization_id)
        .order_by(Device.hostname.asc())
    ).all()
    return [_response(device) for device in devices]


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeviceResponse:
    _ensure_admin(user)
    device = _get_tenant_device(db, device_id, user.organization_id)
    return _response(device)
