# Nexus Retail

Live deployment: [nexus-retail-allocation.vercel.app](https://nexus-retail-allocation.vercel.app)

**An Autonomous Multi-Agent Framework for Coordinated Online and Offline Retail Inventory Allocation**

A working local full-stack demonstration of demand-driven inventory coordination. React dashboards call a FastAPI backend backed by SQLAlchemy and SQLite locally or PostgreSQL in Docker. Ten deterministic agents produce audited recommendations, SciPy performs integer transportation optimization, and an authorized human must explicitly approve every inventory movement. No paid LLM API is required.

Vercel deployment configuration is also included: the React frontend and Python API run in one project with persistent Neon PostgreSQL, an isolated database schema, request-bound cloud workflows and API polling. See [Vercel deployment details](docs/vercel-deployment.md).

## Included capabilities

- Ten connected pages: executive dashboard, inventory, agent control, forecasts, allocation approvals, warehouse utilization, logistics, analytics, scenario simulations and settings.
- JWT login, bcrypt passwords, five roles, configurable CORS, request validation and rate limits.
- 100 products in six retail categories; five warehouses, fifteen stores, one online center and one distribution center; 84,800 weekly sales observations spanning 53 weeks.
- Moving average, exponential smoothing, linear regression and seeded random forest forecasts, fallback for sparse history, approximate uncertainty intervals and rolling holdout errors.
- Integer stock allocation with source reservations/safety protection, destination storage and fulfillment limits, online priorities and distance-based route costs. Deterministic greedy fallback is selectable and documented.
- Persisted agent executions, structured messages, workflow state transitions, actual WebSocket events and polling fallback.
- Atomic approval, version checks, duplicate approval protection, rejection, auditable inventory adjustment and compensating rollback.
- Seven isolated simulations with baseline/optimized shortages and cost comparisons.
- CSV exports and browser print/save-to-PDF reports. No external email, carrier, supplier or point-of-sale integration is implied.

## Requirements

Python 3.12+, Node 22.12+ or 24, and npm or pnpm. Docker Desktop is optional. Commands below run from the repository root unless a `cd` changes directories.

### Backend setup

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
cd backend
..\.venv\Scripts\python -m alembic upgrade head
..\.venv\Scripts\python seed.py
..\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python seed.py
../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Alternatively, use an activated virtual environment and the requested standard commands: `pip install -r requirements.txt` and `uvicorn app.main:app --reload` from `backend/`, after migration and seeding.

The seed command is idempotent and does not reset existing data. Local SQLite lives in `backend/retail.db` when started there. Migrations are explicit; app startup checks interrupted workflows but does not silently create schema or reset stock.

### Frontend setup

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the printed address, normally [http://127.0.0.1:5173](http://127.0.0.1:5173). `pnpm install` and `pnpm dev` are equivalent; the committed pnpm lockfile provides a reproducible pnpm installation. The frontend proxies API and WebSocket requests to port 8000 by default.

If npm is absent in the Codex desktop runtime, the bundled package manager on this machine is:

```powershell
& 'C:\Users\N.ASRITHAREDDY\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd' install
& 'C:\Users\N.ASRITHAREDDY\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd' dev
```

If ports are occupied, start backend on another port and set the frontend proxy accordingly:

```powershell
# Backend terminal, from backend/
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
# Frontend terminal, from frontend/
$env:API_PROXY_TARGET='http://127.0.0.1:8011'
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5181 --strictPort
```

### Demo accounts

Default local password: **`RetailDemo!2026`**. Set `SEED_PASSWORD` before the first seed to choose another password; changing it afterward does not overwrite existing accounts.

| Email | Role | Permissions |
|---|---|---|
| admin@retail.local | Administrator | All actions, including roles |
| inventory@retail.local | Inventory Manager | Forecast, optimize, approve/reject/rollback, edit stock and products |
| warehouse@retail.local | Warehouse Manager | Stock adjustments, transfer proposals and tracking |
| store@retail.local | Store Manager | Read-only network visibility |
| analyst@retail.local | Analyst | Read-only analytics, forecasts and exports |

Store and warehouse role visibility is network-wide in this demonstration, not tenant/store-scoped. Login tokens expire after eight hours. In local development, an unset JWT_SECRET generates an ephemeral secret, invalidating sessions on restart. Production requires a persistent secret of at least 32 characters.

## Try the complete workflow

1. Sign in as the administrator or inventory manager.
2. Inspect Inventory, including low-stock and reserved units.
3. Open Demand forecasting, select a product/location/model, and generate a forecast.
4. Open Inventory allocation and choose **Run Intelligent Allocation**.
5. Watch actual agent states/messages in Agent control. The run advances to **waiting for approval**.
6. Review source/destination, before/after stock, integer quantities, reasons, route ETA and modeled cost. Export the report if needed.
7. Click **Approve allocation**, then **Confirm approve**. Approval revalidates the locked live inventory. Stale proposals return 409 and require a new run.
8. Inspect updated stock, transfer tracking and the audit trail. Dispatch and delivery update tracking only; they do not post stock twice.
9. Before any affected inventory changes again, use **Compensating rollback** to reverse an approved plan. This is a new audited transaction, not deletion of history.
10. Run Simulation center scenarios and compare outcomes without changing live stock.

New products receive zero-stock records at each active location; an authorized operator can enter starting stock from Inventory. Product deletion is a soft deactivation to preserve historical references.

## API and configuration

Interactive OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Health: `/health`. Standard requests use `Authorization: Bearer <token>`. Login accepts JSON `{ "email": "admin@retail.local", "password": "..." }` at `/api/auth/login`.

All requested route groups are implemented: `/api/dashboard/*`, `/api/products`, `/api/inventory`, `/api/forecast`, `/api/agents`, `/api/optimization/runs`, `/api/transfers`, `/api/analytics/*`, `/api/simulation/*`, and `/api/notifications`. Additional routes expose locations, historical sales, audit history, purchase orders, settings, roles and CSV reports. WebSocket `/ws` authenticates using a first JSON frame `{ "token": "..." }`; `/api/events?after=0` provides an authenticated event cursor. List endpoints use documented query parameters; inventory/products support `page_no`, `page_size`, filtering and sorting. Run histories are bounded to 100 and simulation history to 50.

| Variable | Purpose |
|---|---|
| DATABASE_URL | SQLAlchemy URL; default `sqlite:///./retail.db` |
| JWT_SECRET | Persistent JWT signing secret; required in production |
| SEED_PASSWORD | Password for initial synthetic accounts |
| APP_ENV | `production` enforces JWT secret validation |
| CORS_ORIGINS | Comma-separated allowed browser origins |
| API_PROXY_TARGET | Vite API target; default `http://127.0.0.1:8000` |
| VITE_API_URL | Optional separate HTTP API origin; same-origin deployment is recommended |

Export environment variables in the shell before migration, seed and app startup. `.env.example` is a template, not automatically loaded by Python; `uvicorn --env-file .env` or exported variables can load it. Docker Compose reads root `.env` automatically.

## Tests and build

```powershell
cd backend
..\.venv\Scripts\python -m pytest -q
cd ../frontend
npm test
npm run build
```

Tests use a fresh temporary SQLite database under `backend/`, never your demo stock. All 16 backend tests and seven frontend tests passed. Backend coverage includes login/RBAC, product/stock APIs, all four forecasting methods, all ten agents and structured messages, constrained plans, approval/conservation/audits, duplicate concurrent approvals, rollback, stale proposals, failure handling, all seven isolated simulations, WebSocket authentication, exports, analytics, personal notification preferences and explicit migration roundtrips. Frontend component integration tests use mocked HTTP responses; a real browser smoke check verifies login, database metrics, optimization results and the confirmation gate.

During this implementation, Windows sandbox networking blocked asyncio's local socket pair. Tests passed when run with local networking permitted. This is a host restriction, not an application dependency.

## Docker / PostgreSQL

```bash
cp .env.example .env
# Edit POSTGRES_PASSWORD, JWT_SECRET and SEED_PASSWORD first.
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080). Backend is bound to local port 8000. PostgreSQL has a named persistent volume and health checks; backend runs migrations and idempotent seeding before serving; Nginx serves the built client and proxies API/WebSocket traffic. Redis is not required for the single-process implementation.

Docker is not installed on the implementation host, so image builds and the PostgreSQL container path have not been runtime-verified here. PostgreSQL was subsequently verified on Vercel using the attached Neon database, including migrations, seeding, login and optimization. SQLite tests, production frontend build and local HTTP/browser workflows were also verified. Do not treat the Docker configuration as a tested deployment until running it on a Docker-enabled host.

## Operational boundaries

- Local/Docker mode uses one backend process for background workflows and WebSocket events. Vercel mode executes work within the request and uses PostgreSQL polling across instances. Rate-limit counters remain per-instance; execution/message/audit records are durable. Local interrupted jobs are marked failed on restart; cloud cold starts do not invalidate other instances' jobs.
- Optimizer is a sequential multi-product heuristic with exact per-product MILP subproblems; shared capacity is consumed in product-ID order. It does not claim a globally optimal multi-product solution. SciPy is the working OR-Tools alternative.
- ETA, pricing suggestions, promotion uplift and shortage costs are synthetic models. Supplier delays are represented as reduced immediately available supply. No real supplier/order/pricing system is connected.
- Available stock is derived from on-hand minus reservations. Approval posts source and destination stock together; physical transit is tracked separately without a separate in-transit stock location.
- Forecast confidence is an error-derived score and intervals are approximate. Historical inputs are weekly aggregates. Turnover is annual sales/current stock, and savings are modeled cost avoidance rather than realized profit.
- Reports export CSV directly. PDF export uses the browser's print-to-PDF support.
- The interface uses authored CSS rather than adding Tailwind solely for styling. PostgreSQL is configured for Docker, SQLite is the verified local fallback.

See [architecture](docs/architecture.md), [agent workflow](docs/agent_workflow.md), [database schema](docs/database_schema.md) and [optimization methodology](docs/optimization_methodology.md) for details.

## Troubleshooting

- **No such table:** run Alembic from `backend/` using the same DATABASE_URL as the server.
- **401 after restart:** sign in again or configure a persistent JWT_SECRET.
- **409 on approval:** stock changed after the proposal, or it was already approved/rejected. Generate a new plan; do not bypass version checks.
- **No savings yet:** only currently approved optimization runs contribute to the executive savings metric.
- **Frontend cannot connect:** verify backend health and Vite API_PROXY_TARGET; use the port actually printed by Vite.
- **WebSocket unavailable:** views refresh every 15 seconds automatically. Reopen the app to retry the socket.
- **Slow random forest full-network run:** use exponential smoothing for interactive whole-network optimization; compare forests on individual product/location series.
- **Port occupied:** choose alternative ports as shown above; do not stop unrelated services.
- **Fresh dataset needed:** preserve the current database first, then explicitly choose a new DATABASE_URL, migrate and seed it. The seed script never clears your data.
