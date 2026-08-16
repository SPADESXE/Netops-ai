from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InterfacePayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    mac_address: str | None = None
    ipv4_address: str | None = None
    gateway: str | None = None
    dns_servers: list[str] = Field(default_factory=list)
    is_primary: bool = False


class DeviceRegisterRequest(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    username: str | None = Field(default=None, max_length=255)
    os_name: str | None = Field(default=None, max_length=100)
    os_version: str | None = Field(default=None, max_length=100)
    agent_version: str | None = Field(default=None, max_length=50)
    interfaces: list[InterfacePayload] = Field(default_factory=list)


class DeviceRegisterResponse(BaseModel):
    device_id: UUID
    agent_secret: str
    message: str


class HeartbeatRequest(BaseModel):
    interface_name: str | None = None
    ip_address: str | None = None


class MetricsRequest(BaseModel):
    gateway_latency_ms: float | None = Field(default=None, ge=0)
    internet_latency_ms: float | None = Field(default=None, ge=0)
    packet_loss_pct: float | None = Field(default=None, ge=0, le=100)


class InterfaceResponse(BaseModel):
    id: UUID
    name: str
    mac_address: str | None
    ipv4_address: str | None
    gateway: str | None
    dns_servers: list[str]
    is_primary: bool


class DeviceResponse(BaseModel):
    id: UUID
    hostname: str
    username: str | None
    os_name: str | None
    os_version: str | None
    agent_version: str | None
    last_seen_at: datetime | None
    online: bool
    gateway_latency_ms: float | None
    internet_latency_ms: float | None
    packet_loss_pct: float | None
    interfaces: list[InterfaceResponse]
