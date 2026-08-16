# NetOpsAI Day 2 integration notes

This bundle preserves the Day 1 module structure and the existing `Device` / `NetworkInterface` model names.

## Files added

- `backend/app/api/routes/auth.py` — only included because the uploaded Day 1 archive did not contain the backend auth implementation used by the supplied frontend patch.
- `backend/app/api/routes/devices.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/devices.py`
- `backend/app/security/auth.py`
- `backend/app/security/agent_auth.py`
- `backend/app/security/passwords.py`
- `backend/app/core/device_status.py`
- `agent/netops_agent.py`
- `agent/requirements.txt`
- `agent/README.md`

## Files modified

- `backend/app/models/device.py` — machine credential hash + telemetry fields
- `backend/app/models/network_interface.py` — explicit boolean primary flag + update timestamp behavior
- `backend/app/core/config.py` — heartbeat/agent intervals
- `backend/app/main.py` — routers + model registration + development table bootstrap
- `backend/requirements.txt` — `psutil`
- `.env.example` — Day 2 settings
- `frontend/app/page.tsx` — authenticated device list with 15-second polling

## Security behavior

- Admin `/api/v1/devices/register` is tenant-scoped by the authenticated user's organization.
- Registration returns the machine secret once.
- Only the Argon2 hash is stored in PostgreSQL.
- Heartbeat and metrics use `X-Agent-Secret`, never the user's JWT.
- Admin list/get queries always filter by `organization_id`.
- Agent-supplied `online` is never accepted.
- Admin status is computed from `last_seen_at` against `AGENT_HEARTBEAT_TIMEOUT_SECONDS`.

## Registration sequence

1. Log into the Day 1 admin frontend.
2. Copy the returned JWT from browser local storage (`netopsai_token`) for the first agent run.
3. On the development Windows/Linux machine, run the agent with `NETOPSAI_ADMIN_JWT` set.
4. The agent registers once and writes `.netopsai-agent.json`.
5. Subsequent heartbeats and metrics use only the machine secret.

The starter archive did not contain Alembic migrations, so Day 2 uses SQLAlchemy `Base.metadata.create_all()` at application startup for local development. Replace this with the project's migration system when that existing system is present; no new migration framework is introduced here.
