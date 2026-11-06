import {
  Activity,
  ArrowUpRight,
  Box,
  ChartNoAxesCombined,
  Globe,
  Network,
  Package,
  RefreshCw,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";
import { errorText, money, number, useData } from "../api";
import {
  Badge,
  Bars,
  Card,
  Empty,
  ErrorBox,
  Loading,
  Metric,
  Table,
  TrendChart,
} from "../components";
import type { Execution, Run, Summary } from "../types";
export default function Dashboard() {
  const s = useData<Summary>("/api/dashboard/summary");
  const sales = useData<Record<string, unknown>[]>(
    "/api/dashboard/sales-performance",
  );
  const health = useData<{
    statuses: { name: string; value: number }[];
    locations: { name: string; value: number }[];
  }>("/api/dashboard/inventory-health");
  const channels = useData<{ name: string; value: number }[]>(
    "/api/dashboard/channel-performance",
  );
  const logs = useData<{ executions: Execution[] }>("/api/agents/logs");
  const runs = useData<Run[]>("/api/optimization/runs");
  if (s.isPending) return <Loading />;
  if (s.error) return <ErrorBox message={errorText(s.error)} />;
  const d = s.data!;
  return (
    <>
      <div className="overview-banner">
        <div className="banner-icon">
          <Sparkles size={24} />
        </div>
        <div>
          <strong>Your network, working as one.</strong>
          <p>
            Coordinate {d.total_stores} stores and {d.total_warehouses} supply
            locations with demand-aware allocation.
          </p>
        </div>
        <Link to="/allocation" className="primary">
          Intelligent allocation <ArrowUpRight size={16} />
        </Link>
      </div>
      <div className="metrics">
        <Metric
          label="Total inventory"
          value={number(d.total_inventory)}
          detail="Units across the retail network"
          icon={<Package size={18} />}
        />
        <Metric
          label="Inventory value"
          value={money(d.inventory_value)}
          detail={`${d.total_products} active products`}
          icon={<Box size={18} />}
        />
        <Metric
          label="Stock health alerts"
          value={number(d.low_stock)}
          detail={`${number(d.stockout_risk)}% of inventory records at risk`}
          icon={<Activity size={18} />}
        />
        <Metric
          label="Modeled cost savings"
          value={money(d.estimated_savings)}
          detail="Approved allocation cost avoidance"
          icon={<ChartNoAxesCombined size={18} />}
        />
      </div>
      <div className="grid-two wide">
        <Card
          title="Sales performance"
          subtitle="Historical units sold · 53 weeks, grouped by month"
          action={<span className="subtle-chip">Online + offline</span>}
        >
          <TrendChart data={sales.data || []} />
        </Card>
        <Card title="Channel inventory" subtitle="Current on-hand units">
          <div className="distribution-total">
            <strong>{number(d.total_inventory)}</strong>
            <span>units in the network</span>
          </div>
          <div className="distribution-bar">
            {channels.data?.map((c, i) => (
              <span
                key={c.name}
                style={{
                  width: `${(100 * c.value) / d.total_inventory}%`,
                  background: ["#3676ee", "#19b6a1", "#13284a", "#a4bbde"][i],
                }}
              />
            ))}
          </div>
          <div className="channel-list">
            {channels.data?.map((c, i) => (
              <div key={c.name}>
                <span>
                  <i
                    style={{
                      background: ["#3676ee", "#19b6a1", "#13284a", "#a4bbde"][
                        i
                      ],
                    }}
                  />
                  {c.name.replace("_", " ")}
                </span>
                <strong>{number(c.value)}</strong>
                <small>
                  {((100 * c.value) / d.total_inventory).toFixed(1)}%
                </small>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <div className="mini-metrics">
        <div>
          <Globe />
          <strong>{number(d.online_inventory)}</strong>
          <span>Online fulfillment units</span>
        </div>
        <div>
          <ShoppingBag />
          <strong>{number(d.offline_inventory)}</strong>
          <span>Physical store units</span>
        </div>
        <div>
          <RefreshCw />
          <strong>{number(d.inventory_turnover)}×</strong>
          <span>Sales / current stock proxy</span>
        </div>
        <div>
          <ShieldCheck />
          <strong>
            {d.forecast_accuracy == null
              ? "Not run"
              : `${number(d.forecast_accuracy)}%`}
          </strong>
          <span>Forecast holdout accuracy</span>
        </div>
      </div>
      <div className="grid-two">
        <Card
          title="Inventory across the network"
          subtitle="Warehouses and distribution center"
        >
          <Bars
            data={(health.data?.locations || [])
              .filter(
                (l) =>
                  l.name.includes("Warehouse") ||
                  l.name.includes("Distribution"),
              )
              .map((l) => ({ ...l, name: l.name.split(" ")[0] }))}
          />
        </Card>
        <Card
          title="Agent activity"
          subtitle="Actual execution history"
          action={<Link to="/agents">Control center ↗</Link>}
        >
          {logs.data?.executions.length ? (
            <div className="timeline">
              {logs.data.executions.slice(0, 5).map((e) => (
                <div key={e.id}>
                  <div className="timeline-dot">
                    <Network size={15} />
                  </div>
                  <div>
                    <strong>
                      {e.agent_name.charAt(0).toUpperCase() +
                        e.agent_name.slice(1)}{" "}
                      agent <Badge value={e.status} />
                    </strong>
                    <p>
                      {Object.entries(e.output_summary)
                        .slice(0, 2)
                        .map(
                          ([k, v]) =>
                            `${k.replaceAll("_", " ")}: ${typeof v === "object" ? "structured recommendation" : v}`,
                        )
                        .join(" · ")}
                    </p>
                    <small>
                      {new Date(e.created_at).toLocaleTimeString()} ·{" "}
                      {e.execution_duration}s
                    </small>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Empty text="Your agents are ready. Start an allocation to see their decisions here." />
          )}
        </Card>
      </div>
      <Card
        title="Allocation history"
        subtitle="Auditable proposals and approved movements"
        action={<Link to="/allocation">View all ↗</Link>}
      >
        {runs.data?.length ? (
          <Table headers={["Run", "Created", "Units", "Cost", "Status"]}>
            {runs.data.slice(0, 5).map((r) => (
              <tr key={r.id}>
                <td>
                  <Link to={`/allocation?run=${r.id}`}>
                    {r.run_name}
                    <small>{r.id.slice(0, 8)}</small>
                  </Link>
                </td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>{number(r.total_allocated)}</td>
                <td>{money(r.total_cost)}</td>
                <td>
                  <Badge value={r.status} />
                </td>
              </tr>
            ))}
          </Table>
        ) : (
          <Empty text="No allocations yet. Your first intelligent allocation starts here." />
        )}
      </Card>
    </>
  );
}
