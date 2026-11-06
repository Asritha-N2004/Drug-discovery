# Database schema

Normalized entities: roles → users; products and locations → inventory and sales_history; products/locations → demand_forecasts; optimization_runs → inventory_allocations → transfers; agent_executions and agent_messages identify the workflow; audit_logs reference actors. Suppliers → purchase_orders reference products and locations. Promotions, notifications, simulation_runs and settings store ancillary state.

Unique constraints: role name, email, SKU, product/location inventory pair, transfer allocation ID. Inventory checks protect nonnegative reservations and on-hand stock; allocation checks protect positive integer quantities and distinct locations. Foreign keys are enabled explicitly on SQLite. Indexed fields include sales dates, product/location references, inventory pairs, workflow IDs, run statuses and product categories/names.

Money uses Numeric(12,2), Numeric(14,2) or Numeric(16,2). Calculations of simulated route costs use rounded floats before fixed-scale database storage; this is a cost model rather than an accounting ledger. Inventory available is derived from on-hand minus reservations to prevent stored-field drift. Optimistic versions increment on adjustments, approvals and rollback.

Alembic revision 0001 freezes the initial schema into explicit create/drop operations. Future schema changes should use new Alembic revisions; do not edit the initial revision to mutate a deployed database.

Synthetic history consists of weekly aggregate sales for 53 weeks, not individual POS transactions. Date bounds are fixed at 2025-11-06 through 2026-11-05 for reproducibility. All locations, products, users and sales are demonstration records.
