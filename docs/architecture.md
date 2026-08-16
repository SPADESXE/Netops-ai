# NetOpsAI Day 1 Architecture

## Product flow

Observe → Diagnose → Explain → Simulate → Approve → Fix → Verify

## Day 1 runtime

Browser
  ↓
Next.js
  ↓
FastAPI
  ├── PostgreSQL
  └── Redis

## Future runtime

Endpoint agents / SNMP / cloud APIs
  ↓
Telemetry + event layer
  ↓
Diagnostic workers
  ↓
AI tool layer
  ↓
Simulation
  ↓
Approval/policy engine
  ↓
Remediation
  ↓
Verification

## Multi-tenancy

Every tenant-owned table will include an `organization_id` directly or through a tenant-owned parent. API authorization will enforce tenant boundaries.

## Security principle

The AI never receives unrestricted shell or network credentials. Any network-affecting action must go through typed tools and policy checks.
