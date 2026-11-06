# Verification record — 6 November 2026

- Explicit Alembic migration: upgrade → downgrade → upgrade on a fresh database passed.
- Synthetic seed: 100 products, 22 locations, 2,200 stock records and 84,800 sales records. Idempotent rerun passed.
- Backend: **13 passed**, final run 39.86 seconds. Test database is isolated from demo inventory.
- Frontend: **7 passed**, final run 5.46 seconds; TypeScript compilation passed.
- Production build: passed, 13.07 seconds; chart/framework/query chunks split, largest JS chunk 412.13 kB before gzip.
- Real browser smoke check: login, dashboard metrics, allocation generation, recommendation projections and explicit approval dialog observed.
- Demo allocation: 27,373 units in 983 movements; modeled shortage target 30,346 → 2,973, 90.2% reduction. These are synthetic model outputs. Plan remains waiting for approval.
- Full approval, duplicate/concurrent approval rejection, stock conservation, audit creation and compensating rollback verified through integration tests.
- No real inventory system, carrier or pricing service was contacted.
- Docker executable unavailable; image builds, Compose service startup and PostgreSQL runtime remain unverified. The Compose configuration is supplied for a Docker-enabled host.
- Runtime caveat: use one backend worker; shared event broadcasting and rate limiting are process-local.

The browser preview during implementation used UI port 5181 and API port 8011 because default ports were occupied. See README for normal and alternate-port commands.

## Vercel production verification

- Production deployment READY: `dpl_CYJNiGsdsJAy4NSWkjxQfCXWKuZe`.
- Public URL: https://nexus-retail-allocation.vercel.app
- Attached Neon PostgreSQL initialized in isolated `nexus_inventory_v1` schema; existing application tables preserved.
- Cloud login, database metrics, PostgreSQL monthly-sales query, ten-agent allocation and sandbox simulation verified.
- Public API smoke check passed health, login, inventory, run/simulation history, all analytics routes, settings, notifications and React deep links.
- Current regression suite: **16 backend tests** and **7 frontend tests** passed; TypeScript and production builds passed.
- Cloud workflow: 27,373 recommended units; remains waiting for approval. Cloud online-surge simulation: 70,139 simulated demand units and 71.9% modeled shortage reduction. No live inventory was changed by these verification scenarios.
- Runtime on Vercel uses request-bound workflow execution and database polling; Docker remains unverified because Docker is absent locally.
