# NetOpsAI — Day 1 Starter

20-day MVP: AI-powered network monitoring, diagnostics, simulation and safe remediation.

## Day 1 stack

- Frontend: Next.js 16.2.11 + TypeScript
- Backend: FastAPI + Python 3.12
- Database: PostgreSQL 18
- Cache: Redis
- Local orchestration: Docker Compose

## Start

1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Run:

```bash
docker compose up --build
```

4. Open:
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - Swagger: http://localhost:8000/docs

## Stop

```bash
docker compose down
```

To remove database/cache volumes too:

```bash
docker compose down -v
```

## Day 1 deliverables

- Next.js frontend shell
- FastAPI backend
- PostgreSQL connection
- Redis connection
- Health endpoint
- Initial multi-tenant data model
- JWT-ready authentication module structure

Day 2 will build the real auth endpoints and backend service layer on top of this foundation.
