# Architecture

React / TypeScript / Vite → same-origin proxy → FastAPI → SQLAlchemy → PostgreSQL (Docker) or SQLite (local).

React Query refreshes database-backed views every 15 seconds. A first-frame-authenticated WebSocket invalidates the same caches on actual backend events. Login tokens are held in sessionStorage. Passwords use bcrypt, JWTs expire after eight hours, and every write endpoint checks an explicit role dependency. Login and workflow initiation have bounded per-process rate limits. CORS origins are an environment setting.

The coordinator runs synchronous CPU tasks through FastAPI BackgroundTasks' thread pool. Each execution has persisted inputs, outputs, timing, status, confidence where meaningful, and structured messages. Queued/running jobs are marked failed after a process restart. Proposed inventory never changes stock. SQLite approval uses BEGIN IMMEDIATE; PostgreSQL uses ordered row locks. Stock versions invalidate stale proposals. All stock mutations and ledger/audit records commit together.

Local and Docker mode use exactly one Uvicorn worker. Vercel mode executes workflows within their initiating request and polls persisted PostgreSQL data across function instances. Events and rate counters remain in memory, while executions, messages and audits are durable. Large asynchronous workloads still require a durable queue plus shared pub/sub and distributed rate limiting. Redis is intentionally omitted until those consumers exist. No paid model provider or external logistics service is required.

Source modules are organized by behavior rather than empty directory scaffolding: models, schemas, security, forecasting, optimization, agents, transactions, analytics, events, seed, and HTTP routes. The React application uses shared API hooks, typed entities, reusable charts/cards/tables and routed functional pages.
