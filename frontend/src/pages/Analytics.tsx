import { Download } from "lucide-react";
import { csvDownload, money, number, useData } from "../api";
import { Badge, Bars, Card, Empty, Metric, Table } from "../components";
import type { Summary } from "../types";
export default function Analytics() {
  const s = useData<Summary>("/api/dashboard/summary");
  const accuracy = useData<
    {
      model: string;
      mae: number;
      wape: number;
      accuracy: number;
      predictions: number;
    }[]
  >("/api/analytics/forecast-accuracy");
  const performance = useData<Record<string, unknown>[]>(
    "/api/analytics/allocation-performance",
  );
  const health = useData<{
    statuses: { name: string; value: number }[];
    locations: { name: string; value: number }[];
  }>("/api/dashboard/inventory-health");
  const channels = useData<Record<string, unknown>[]>(
    "/api/dashboard/channel-performance",
  );
  const d = s.data;
  return (
    <>
      <div className="section-toolbar">
        <span className="note">
          Modeled savings use configured shortage penalties. Turnover uses
          current stock as a proxy.
        </span>
        <div className="button-row">
          <button
            onClick={() =>
              csvDownload(performance.data || [], "allocation-performance.csv")
            }
          >
            <Download size={16} />
            Export CSV
          </button>
          <button onClick={() => window.print()}>Print / save PDF</button>
        </div>
      </div>
      <div className="metrics">
        <Metric
          label="Turnover proxy"
          value={`${number(d?.inventory_turnover)}×`}
        />
        <Metric label="Overstock records" value={number(d?.overstock)} />
        <Metric
          label="Forecast accuracy"
          value={
            d?.forecast_accuracy == null
              ? "Not run"
              : `${number(d.forecast_accuracy)}%`
          }
        />
        <Metric
          label="Modeled cost avoidance"
          value={money(d?.estimated_savings)}
        />
      </div>
      <div className="grid-two">
        <Card
          title="Allocation outcomes"
          subtitle="Actual completed optimization results"
        >
          <Bars
            data={(performance.data || [])
              .slice(-10)
              .map((r) => ({ ...r, name: String(r.id).slice(0, 6) }))}
            keys={["baseline_shortage", "optimized_shortage"]}
          />
        </Card>
        <Card title="Inventory health" subtitle="Inventory records by status">
          <Bars data={health.data?.statuses || []} />
        </Card>
        <Card
          title="Channel inventory utilization"
          subtitle="Current units by network location type"
        >
          <Bars data={channels.data || []} />
        </Card>
        <Card
          title="Model validation"
          subtitle="Rolling holdout MAE and weighted absolute percentage error"
        >
          {accuracy.data?.length ? (
            <Table
              headers={["Model", "MAE", "WAPE", "Accuracy", "Predictions"]}
            >
              {accuracy.data.map((a) => (
                <tr key={a.model}>
                  <td>{a.model.replaceAll("_", " ")}</td>
                  <td>{number(a.mae)}</td>
                  <td>{number(a.wape * 100)}%</td>
                  <td>{number(a.accuracy)}%</td>
                  <td>{number(a.predictions)}</td>
                </tr>
              ))}
            </Table>
          ) : (
            <Empty text="Run forecasts to generate validation metrics." />
          )}
        </Card>
      </div>
      <Card
        title="Cost and allocation ledger"
        subtitle="Proposed and approved outcomes are labeled separately"
      >
        <Table
          headers={[
            "Run",
            "Status",
            "Allocated units",
            "Transfer costs",
            "Cost avoidance",
          ]}
        >
          {performance.data?.map((r, i) => (
            <tr key={i}>
              <td>{String(r.id).slice(0, 8)}</td>
              <td>
                <Badge value={String(r.status)} />
              </td>
              <td>{number(Number(r.allocated))}</td>
              <td>{money(Number(r.cost))}</td>
              <td>{money(Number(r.estimated_savings || 0))}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </>
  );
}
