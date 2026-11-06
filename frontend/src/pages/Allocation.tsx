import {
  ArrowUpRight,
  Check,
  ChevronRight,
  Download,
  Globe,
  Network,
  ShoppingBag,
  Sparkles,
  Warehouse,
  X,
} from "lucide-react";
import { useContext, useState } from "react";
import { Link } from "react-router-dom";
import { api, csvDownload, errorText, money, number, useData } from "../api";
import {
  Badge,
  Card,
  Drawer,
  Empty,
  ErrorBox,
  Loading,
  Metric,
  Table,
} from "../components";
import { Auth, useAction } from "../context";
import type { Recommendation, Run } from "../types";
export default function Allocation() {
  const { canManage } = useContext(Auth);
  const runs = useData<Run[]>("/api/optimization/runs");
  const [chosen, setChosen] = useState(
    new URLSearchParams(location.search).get("run") || "",
  );
  const [selected, setSelected] = useState<Recommendation | null>(null);
  const [confirm, setConfirm] = useState<
    "approve" | "reject" | "rollback" | null
  >(null);
  const runId = chosen || runs.data?.[0]?.id || "";
  const run = useData<Run>(`/api/optimization/runs/${runId}`, !!runId);
  const recs = useData<Recommendation[]>(
    `/api/optimization/runs/${runId}/recommendations`,
    !!runId,
  );
  const start = useAction<void>(async () => {
    const r = await api.post("/api/optimization/run", {
      run_name: "Demand-balanced network allocation",
    });
    setChosen(r.data.id);
  }, "Optimization workflow started");
  const decision = useAction<string>(
    (action) => api.post(`/api/optimization/runs/${runId}/${action}`),
    "Allocation decision recorded",
  );
  const d = run.data;
  return (
    <>
      <div className="allocation-hero">
        <div>
          <span className="eyebrow">HUMAN APPROVED · AGENT COORDINATED</span>
          <h2>Give every channel the stock it needs.</h2>
          <p>
            Demand forecasts, protected reservations and real capacity
            constraints.
            <br />
            Review every recommendation before it touches your inventory.
          </p>
          <div className="button-row">
            {canManage && (
              <button
                className="primary"
                disabled={
                  start.isPending ||
                  ["queued", "running"].includes(d?.status || "")
                }
                onClick={() => start.mutate()}
              >
                <Sparkles size={17} />
                {start.isPending ? "Starting…" : "Run Intelligent Allocation"}
              </button>
            )}
            <Link to="/agents" className="button">
              View agent workflow <ArrowUpRight size={16} />
            </Link>
          </div>
        </div>
        <div className="allocation-graphic">
          <div>
            <Warehouse />
            <span>SUPPLY</span>
          </div>
          <i>→</i>
          <div className="center">
            <Network />
            <span>COORDINATE</span>
          </div>
          <i>→</i>
          <div>
            <ShoppingBag />
            <Globe />
            <span>DEMAND</span>
          </div>
        </div>
      </div>
      {start.error && <ErrorBox message={errorText(start.error)} />}
      <div className="section-toolbar">
        <div>
          <h3>Allocation workspace</h3>
          <p className="muted">
            Proposals remain read-only until explicitly approved.
          </p>
        </div>
        <select
          aria-label="Select allocation run"
          value={runId}
          onChange={(e) => setChosen(e.target.value)}
        >
          <option value="">Select a run</option>
          {runs.data?.map((r) => (
            <option key={r.id} value={r.id}>
              {r.run_name} · {r.id.slice(0, 8)} · {r.status}
            </option>
          ))}
        </select>
      </div>
      {d && (
        <>
          <div className="run-status">
            <Badge value={d.status} />
            <span>
              Run {d.id.slice(0, 8)} · {new Date(d.created_at).toLocaleString()}
            </span>
            <span className="subtle-chip">
              {d.results.solver?.join(", ") || "Pending solver"}
            </span>
          </div>
          {d.error && <ErrorBox message={d.error} />}
          <div className="metrics">
            <Metric
              label="Recommended movement"
              value={number(d.total_allocated)}
              detail="Integer units · all channels"
            />
            <Metric
              label="Transfer & fulfillment"
              value={money(d.total_cost)}
              detail="Modeled transportation costs"
            />
            <Metric
              label="Shortage reduction"
              value={`${number(d.results.stockout_reduction)}%`}
              detail={`${number(d.results.baseline_shortage)} → ${number(d.results.optimized_shortage)} unmet units`}
            />
            <Metric
              label="Modeled cost avoidance"
              value={money(d.results.estimated_savings)}
              detail={`Objective cost: ${money(d.objective_value)}`}
            />
          </div>
          <Card
            title="Recommended allocations"
            subtitle={`${number(recs.data?.length)} proposed movements · before and after are snapshot projections`}
            action={
              <div className="button-row">
                <button
                  disabled={!recs.data?.length}
                  onClick={() =>
                    csvDownload(
                      (recs.data || []) as unknown as Record<string, unknown>[],
                      "allocation-report.csv",
                    )
                  }
                >
                  <Download size={16} />
                  Export report
                </button>
                {canManage && d.status === "waiting_for_approval" && (
                  <>
                    <button onClick={() => setConfirm("reject")}>
                      <X size={16} />
                      Reject
                    </button>
                    <button
                      className="primary"
                      onClick={() => setConfirm("approve")}
                    >
                      <Check size={16} />
                      Approve allocation
                    </button>
                  </>
                )}
                {canManage && d.status === "approved" && (
                  <button onClick={() => setConfirm("rollback")}>
                    Compensating rollback
                  </button>
                )}
              </div>
            }
          >
            {["running", "queued"].includes(d.status) && <Loading />}
            {recs.data?.length ? (
              <Table
                headers={[
                  "Product",
                  "Source → destination",
                  "Channel",
                  "Before",
                  "Move",
                  "After",
                  "Cost",
                  "",
                ]}
              >
                {recs.data.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <strong>{a.product_name}</strong>
                      <small>{a.sku}</small>
                    </td>
                    <td>
                      {a.source}
                      <small>→ {a.destination}</small>
                    </td>
                    <td>
                      <Badge value={a.sales_channel} />
                    </td>
                    <td>{a.before}</td>
                    <td className="positive">+{a.allocated_quantity}</td>
                    <td>
                      <strong>{a.after}</strong>
                    </td>
                    <td>{money(a.estimated_cost)}</td>
                    <td>
                      <button
                        aria-label={`Allocation details ${a.id}`}
                        className="icon-button"
                        onClick={() => setSelected(a)}
                      >
                        <ChevronRight size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </Table>
            ) : (
              !["running", "queued"].includes(d.status) && (
                <Empty text="No inventory movement recommended for this run." />
              )
            )}
          </Card>
        </>
      )}
      {!runId && (
        <Card>
          <Empty text="Run your first intelligent allocation to generate a demand-balanced plan." />
        </Card>
      )}
      {selected && (
        <Drawer
          title="Allocation explanation"
          onClose={() => setSelected(null)}
        >
          <h3>{selected.product_name}</h3>
          <p>
            {selected.source} → {selected.destination}
          </p>
          <p>{selected.reason}</p>
          <div className="metrics two">
            <Metric
              label="Quantity"
              value={number(selected.allocated_quantity)}
            />
            <Metric
              label="Estimated route time"
              value={`${selected.eta_hours}h`}
            />
          </div>
          <p>
            Projected stock: {selected.before} → {selected.after}
          </p>
          <p>Cost: {money(selected.estimated_cost)}</p>
        </Drawer>
      )}
      {confirm && (
        <Drawer
          title={`${confirm.charAt(0).toUpperCase() + confirm.slice(1)} allocation`}
          onClose={() => {
            setConfirm(null);
            decision.reset();
          }}
        >
          <p>
            {confirm === "approve"
              ? `Approve ${number(d?.total_allocated)} units of inventory movement? This atomically updates both source and destination stock and creates transfer tracking records.`
              : confirm === "rollback"
                ? "Reverse the posted inventory movements with an audited compensating transaction? This requires unchanged stock versions."
                : "Reject this proposal? Inventory will remain unchanged."}
          </p>
          <p>
            All reservations, versions and capacities are revalidated by the
            server.
          </p>
          {decision.error && <ErrorBox message={errorText(decision.error)} />}
          <button
            className="primary"
            disabled={decision.isPending}
            onClick={() =>
              decision.mutate(confirm, { onSuccess: () => setConfirm(null) })
            }
          >
            {decision.isPending ? "Processing…" : `Confirm ${confirm}`}
          </button>
        </Drawer>
      )}
    </>
  );
}
