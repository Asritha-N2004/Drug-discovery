# Vercel deployment

Production: https://nexus-retail-allocation.vercel.app

Verified on 6 November 2026 in the `resum-projects` workspace. Production deployment ID: `dpl_CYJNiGsdsJAy4NSWkjxQfCXWKuZe`. Vercel reported READY and assigned the production domain. Live API checks verified PostgreSQL health, login, 100 products, 199,079 stock units, thirteen monthly sales buckets, ten agents, inventory, analytics, settings, notifications, simulation history and React application routes. A cloud allocation and an isolated simulation completed on the preview sharing the isolated application schema; the allocation remains waiting for approval.

The account rejected direct preview promotion, so the verified source was rebuilt with `target=production`. The previously deployed application tables remain in their earlier database schema. A production browser screenshot is saved as `docs/screenshots/vercel-production.png`.

The workspace deploys React static assets and a Python FastAPI function in one Vercel project. `vercel.json` routes `/api/*`, `/health`, `/docs` and `/openapi.json` to `api/index.py`; other application routes use the React entry page. Root requirements are deliberately flat because Vercel's Python requirements parser does not resolve the nested requirements include used in an initial preview attempt.

## Required runtime settings

- `DATABASE_URL`: persistent PostgreSQL URL supplied by the attached Neon integration.
- `DATABASE_URL_UNPOOLED`: preferred when available, so schema selection and initialization advisory locks use a direct PostgreSQL session.
- `JWT_SECRET`: existing persistent signing secret, at least 32 characters.
- `DATABASE_SCHEMA=nexus_inventory_v1`: separate namespace; earlier application tables in other schemas are preserved.
- `CLOUD_INITIALIZE=true`: cold-start bootstrap acquires a PostgreSQL advisory lock, runs explicit Alembic migrations in the selected namespace, then idempotently seeds the synthetic dataset.
- `APP_ENV=production` and `VITE_REALTIME_MODE=polling`.

Secrets remain in Vercel's environment. They are not exported into source files, deployment manifests, logs or this document. Existing sensitive Vercel environment values cannot be decrypted through the account API; the application consumes them inside its runtime.

## Serverless behavior

Cloud allocation execution finishes inside the initiating HTTP request rather than relying on detached background tasks. Execution status, inputs, outputs and messages remain in PostgreSQL. API polling every 15 seconds refreshes views across function instances. Local development continues to use WebSockets and a background thread.

New function instances never mark another instance's workflow failed. This avoids the single-process local startup recovery behavior invalidating work in progress elsewhere. Hosting request duration still limits long jobs; use a durable worker queue before supporting large production workloads.

The first API request can be slower because it initializes schema and synthetic data. Subsequent starts check the applied revision and existing products instead of resetting data. Schema initialization is coordinated through a session-level advisory lock on the direct Neon connection.

`scripts/vercel_deploy.py` uploads an explicit list of application source files through the supported Vercel deployment API using the user's existing local CLI session. It excludes `.venv`, local SQLite data, credentials, node_modules and test data. Preview deployments are checked before production promotion. The deployment state file contains identifiers and URLs only and is ignored by Git.
