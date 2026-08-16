from __future__ import annotations

import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests

API_URL = os.getenv("NETOPSAI_API_URL", "http://localhost:8000")
DEVICE_ID = os.getenv("NETOPSAI_DEVICE_ID")
AGENT_SECRET = os.getenv("NETOPSAI_AGENT_SECRET")
INTERVAL = int(os.getenv("NETOPSAI_INTERVAL_SECONDS", "30"))
STATE_FILE = Path(os.getenv("NETOPSAI_STATE_FILE", ".netopsai-agent.json"))
INTERNET_TARGET = os.getenv("NETOPSAI_INTERNET_TARGET", "1.1.1.1")


def run(command: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout + result.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def get_gateway() -> str | None:
    if platform.system() == "Windows":
        text = run(["powershell", "-NoProfile", "-Command", "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Sort-Object RouteMetric | Select-Object -First 1).NextHop"])
        value = text.strip().splitlines()[0] if text.strip() else ""
        return value or None

    text = run(["ip", "route", "show", "default"])
    match = re.search(r"default via ([0-9a-fA-F:.]+)", text)
    return match.group(1) if match else None


def get_dns_servers() -> list[str]:
    servers: list[str] = []
    if platform.system() == "Windows":
        text = run(["powershell", "-NoProfile", "-Command", "Get-DnsClientServerAddress -AddressFamily IPv4 | ForEach-Object {$_.ServerAddresses}"])
        servers = [line.strip() for line in text.splitlines() if line.strip()]
    else:
        try:
            for line in Path("/etc/resolv.conf").read_text().splitlines():
                match = re.match(r"\s*nameserver\s+([^\s#]+)", line)
                if match:
                    servers.append(match.group(1))
        except OSError:
            pass
    return list(dict.fromkeys(servers))


def get_interfaces(gateway: str | None, dns_servers: list[str]) -> list[dict]:
    interfaces: list[dict] = []
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    for name, entries in addrs.items():
        mac = None
        ipv4 = None
        for entry in entries:
            if entry.family == psutil.AF_LINK:
                mac = entry.address
            elif entry.family == socket.AF_INET:
                ipv4 = entry.address
        if not ipv4 and not mac:
            continue
        interfaces.append(
            {
                "name": name,
                "mac_address": mac,
                "ipv4_address": ipv4,
                "gateway": gateway if ipv4 else None,
                "dns_servers": dns_servers if ipv4 else [],
                "is_primary": bool(stats.get(name) and stats[name].isup and ipv4 and not ipv4.startswith("127.")),
            }
        )

    primary_found = False
    for iface in interfaces:
        if iface["is_primary"] and not primary_found:
            primary_found = True
        elif iface["is_primary"]:
            iface["is_primary"] = False
    if interfaces and not primary_found:
        for iface in interfaces:
            if iface["ipv4_address"] and not iface["ipv4_address"].startswith("127."):
                iface["is_primary"] = True
                break
    return interfaces


def ping(host: str) -> tuple[float | None, float | None]:
    if not host:
        return None, None
    flag = "-n" if platform.system() == "Windows" else "-c"
    output = run(["ping", flag, "4", "-w", "2000", host], timeout=12)
    if not output:
        return None, None

    loss_match = re.search(r"\((\d+(?:\.\d+)?)%\s*(?:packet )?loss\)", output, re.IGNORECASE)
    loss = float(loss_match.group(1)) if loss_match else None

    if platform.system() == "Windows":
        avg_match = re.search(r"Average\s*=\s*(\d+)ms", output, re.IGNORECASE)
        latency = float(avg_match.group(1)) if avg_match else None
    else:
        avg_match = re.search(r"=\s*[0-9.]+/([0-9.]+)/", output)
        latency = float(avg_match.group(1)) if avg_match else None
    return latency, loss


def collect() -> dict:
    gateway = get_gateway()
    dns_servers = get_dns_servers()
    interfaces = get_interfaces(gateway, dns_servers)
    primary = next((iface for iface in interfaces if iface["is_primary"]), interfaces[0] if interfaces else {})
    gateway_latency, _ = ping(gateway) if gateway else (None, None)
    internet_latency, packet_loss = ping(INTERNET_TARGET)
    return {
        "hostname": socket.gethostname(),
        "username": os.getenv("USERNAME") or os.getenv("USER") or "unknown",
        "os_name": platform.system(),
        "os_version": platform.version(),
        "agent_version": "0.1.0",
        "interfaces": interfaces,
        "primary_interface": primary,
        "gateway_latency_ms": gateway_latency,
        "internet_latency_ms": internet_latency,
        "packet_loss_pct": packet_loss,
    }


def register() -> tuple[str, str]:
    info = collect()
    response = requests.post(f"{API_URL}/api/v1/devices/register", json=info, timeout=15)
    response.raise_for_status()
    data = response.json()
    return str(data["device_id"]), str(data["agent_secret"])


def save_state(device_id: str, secret: str) -> None:
    STATE_FILE.write_text(json.dumps({"device_id": device_id, "agent_secret": secret}), encoding="utf-8")


def load_state() -> tuple[str | None, str | None]:
    if not STATE_FILE.exists():
        return None, None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("device_id"), data.get("agent_secret")
    except (OSError, json.JSONDecodeError):
        return None, None


def register_payload(info: dict) -> dict:
    return {
        "hostname": info["hostname"],
        "username": info["username"],
        "os_name": info["os_name"],
        "os_version": info["os_version"],
        "agent_version": info["agent_version"],
        "interfaces": info["interfaces"],
    }


def main() -> int:
    global DEVICE_ID, AGENT_SECRET
    if not DEVICE_ID or not AGENT_SECRET:
        DEVICE_ID, AGENT_SECRET = load_state()

    if not DEVICE_ID or not AGENT_SECRET:
        admin_token = os.getenv("NETOPSAI_ADMIN_JWT")
        if not admin_token:
            print("Set NETOPSAI_ADMIN_JWT for first registration, then the agent will use its machine secret.")
            return 2
        info = collect()
        response = requests.post(
            f"{API_URL}/api/v1/devices/register",
            json=register_payload(info),
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        DEVICE_ID = str(data["device_id"])
        AGENT_SECRET = str(data["agent_secret"])
        save_state(DEVICE_ID, AGENT_SECRET)
        print(f"Registered device {DEVICE_ID}; secret saved to {STATE_FILE}")

    while True:
        try:
            info = collect()
            headers = {"X-Agent-Secret": AGENT_SECRET}
            primary = info["primary_interface"]
            requests.post(
                f"{API_URL}/api/v1/devices/{DEVICE_ID}/heartbeat",
                json={
                    "interface_name": primary.get("name"),
                    "ip_address": primary.get("ipv4_address"),
                },
                headers=headers,
                timeout=10,
            ).raise_for_status()
            requests.post(
                f"{API_URL}/api/v1/devices/{DEVICE_ID}/metrics",
                json={
                    "gateway_latency_ms": info["gateway_latency_ms"],
                    "internet_latency_ms": info["internet_latency_ms"],
                    "packet_loss_pct": info["packet_loss_pct"],
                },
                headers=headers,
                timeout=10,
            ).raise_for_status()
            print(
                f"heartbeat ok | {info['hostname']} | {primary.get('ipv4_address')} | "
                f"gw={info['gateway_latency_ms']}ms internet={info['internet_latency_ms']}ms loss={info['packet_loss_pct']}%"
            )
        except requests.RequestException as exc:
            print(f"agent API error: {exc}", file=sys.stderr)
        except Exception as exc:
            print(f"agent collection error: {exc}", file=sys.stderr)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    raise SystemExit(main())
