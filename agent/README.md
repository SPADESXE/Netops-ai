# NetOpsAI Endpoint Agent — Day 2

## First registration

The first run uses an administrator JWT only to register the endpoint. The API returns a one-time machine secret. The agent stores it in `.netopsai-agent.json` and uses `X-Agent-Secret` for all future heartbeats/metrics.

PowerShell example:

```powershell
$env:NETOPSAI_API_URL="http://localhost:8000"
$env:NETOPSAI_ADMIN_JWT="<admin JWT from the Day 1 login>"
python .\netops_agent.py
```

After first registration, unset `NETOPSAI_ADMIN_JWT`; the local state file is enough for subsequent runs.

## Linux

```bash
export NETOPSAI_API_URL=http://localhost:8000
export NETOPSAI_ADMIN_JWT='<admin JWT from the Day 1 login>'
python3 netops_agent.py
```

## Collected data

- hostname
- username
- OS name/version
- interface name
- IPv4
- MAC
- gateway
- DNS servers
- agent version
- gateway latency
- internet latency to `1.1.1.1`
- packet loss
- heartbeat freshness
