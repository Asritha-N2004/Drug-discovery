# Agent workflow

The workflow states are queued → running → waiting_for_approval → approved / rejected. A failed stage makes the run failed; an unchanged approved allocation can move to rolled_back through a compensating transaction.

1. Supervisor captures the configured workflow and inventory snapshot.
2. Demand produces location/product forecasts, approximate intervals and rolling holdout errors.
3. Monitoring identifies low stock, overstock and inconsistent reservations.
4. Online and offline agents produce channel demand recommendations from shared forecasts.
5. Warehouse calculates available supply after safety stock and reservations.
6. Pricing suggests discounts on excess stock; it never changes selling prices.
7. Risk quantifies low-stock exposure and near-capacity locations.
8. Allocation solves integer shipments using shared stock, forecasts and cost weights.
9. Logistics reports modeled route costs and delivery times.
10. Supervisor validates all constraints and presents the proposal for authorized review.

Each step persists an Execution and sends a Message containing structured output to the supervisor. The shared state includes stock, locations and forecasts; outputs describe the evidence behind the plan. Individual agent controls execute a dependency-inclusive diagnostic workflow, so related outputs are refreshed together. This is explicitly described in the interface.

Administrator and Inventory Manager can approve or reject. Approval locks the run and inventory, checks versions, validates all recommendations cumulatively, posts inventory at both locations, creates tracking transfers, and writes a before/after audit atomically. Transfer statuses are operational tracking; dispatch/delivery do not post stock twice. This simplified ledger posts ownership at approval rather than modeling inventory in transit as a separate location. Rollback requires no intervening updates to affected records and marks transfers reversed.
