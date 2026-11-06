import { Sparkles } from "lucide-react";
import { useContext, useState } from "react";
import { api, errorText, number, useData } from "../api";
import {
  Card,
  Empty,
  ErrorBox,
  Metric,
  Table,
  TrendChart,
} from "../components";
import { models } from "../config";
import { Auth, useAction } from "../context";
import type { Forecast, Location, Page, Product } from "../types";
export default function Forecasting() {
  const { canManage } = useContext(Auth);
  const [product, setProduct] = useState(1);
  const [location, setLocation] = useState(21);
  const [channel, setChannel] = useState("");
  const [model, setModel] = useState("exponential_smoothing");
  const [horizon, setHorizon] = useState(7);
  const [comparisons, setComparisons] = useState<Forecast[]>([]);
  const products = useData<Page<Product>>("/api/products?page_size=200");
  const locations = useData<Location[]>("/api/locations");
  const history = useData<{ date: string; quantity: number }[]>(
    `/api/sales/history?product_id=${product}&location_id=${location}`,
  );
  const forecasts = useData<Forecast[]>(
    `/api/forecast?product_id=${product}&location_id=${location}&channel=${channel}`,
  );
  const run = useAction<void>(async () => {
    const r = await api.post("/api/forecast/run", {
      product_id: product,
      location_id: location,
      model,
      horizon,
    });
    setComparisons((p) => [...p, ...r.data.items].slice(-8));
  }, "Forecast generated");
  const f = forecasts.data?.[0];
  const historical = (history.data || []).slice(-16).map((h) => ({
    date: h.date,
    demand: Math.round((h.quantity / 7) * 10) / 10,
  }));
  const projected = f
    ? [
        {
          date: f.forecast_date,
          predicted: Math.round((f.predicted_demand / f.horizon) * 10) / 10,
          lower: Math.round((f.lower_bound / f.horizon) * 10) / 10,
          upper: Math.round((f.upper_bound / f.horizon) * 10) / 10,
        },
      ]
    : [];
  return (
    <>
      <Card
        title="Forecast configuration"
        subtitle="Compare local statistical models with rolling holdout validation"
      >
        <div className="filters forecast-filters">
          <label>
            Product
            <select
              value={product}
              onChange={(e) => {
                setProduct(+e.target.value);
                setComparisons([]);
              }}
            >
              {products.data?.items.map((p) => (
                <option value={p.id} key={p.id}>
                  {p.sku} · {p.product_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Channel
            <select
              value={channel}
              onChange={(e) => {
                const c = e.target.value;
                setChannel(c);
                const loc = locations.data?.find(
                  (l) =>
                    l.location_type === (c === "online" ? "online" : "store"),
                );
                if (loc) setLocation(loc.id);
              }}
            >
              <option value="">All channels</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
            </select>
          </label>
          <label>
            Location
            <select
              value={location}
              onChange={(e) => {
                setLocation(+e.target.value);
                setComparisons([]);
              }}
            >
              {locations.data
                ?.filter(
                  (l) =>
                    ["store", "online"].includes(l.location_type) &&
                    (!channel ||
                      (channel === "online"
                        ? l.location_type === "online"
                        : l.location_type === "store")),
                )
                .map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.location_name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Model
            <select value={model} onChange={(e) => setModel(e.target.value)}>
              {models.map((m) => (
                <option key={m} value={m}>
                  {m.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            Horizon (days)
            <input
              type="number"
              min="1"
              max="90"
              value={horizon}
              onChange={(e) => setHorizon(+e.target.value)}
            />
          </label>
          {canManage && (
            <button
              className="primary"
              disabled={run.isPending || horizon < 1 || horizon > 90}
              onClick={() => run.mutate()}
            >
              <Sparkles size={16} />
              {run.isPending ? "Forecasting…" : "Generate forecast"}
            </button>
          )}
        </div>
        {run.error && <ErrorBox message={errorText(run.error)} />}
      </Card>
      <div className="metrics">
        <Metric
          label="Predicted demand"
          value={number(f?.predicted_demand)}
          detail={f ? `${f.horizon}-day horizon` : "Run a forecast"}
        />
        <Metric
          label="Prediction interval"
          value={
            f ? `${number(f.lower_bound)} – ${number(f.upper_bound)}` : "—"
          }
          detail="Approximate 95% interval"
        />
        <Metric
          label="Holdout MAE"
          value={number(f?.mae)}
          detail="Units per day · last 4 weeks"
        />
        <Metric
          label="Decision confidence"
          value={f ? `${number(f.confidence_score * 100)}%` : "—"}
          detail={f?.model_name.replaceAll("_", " ") || "No forecast yet"}
        />
      </div>
      <div className="grid-two">
        <Card
          title="Historical demand"
          subtitle="Weekly observations normalized to units per day"
        >
          <TrendChart data={historical} keys={["demand"]} x="date" />
        </Card>
        <Card
          title="Forecast and uncertainty"
          subtitle="Daily expected demand over selected horizon"
        >
          {f ? (
            <TrendChart
              data={[
                ...historical
                  .slice(-6)
                  .map((h) => ({ date: h.date, predicted: h.demand })),
                ...projected,
              ]}
              keys={["predicted", "lower", "upper"]}
              x="date"
            />
          ) : (
            <Empty text="Generate a forecast to see predicted demand and uncertainty." />
          )}
        </Card>
      </div>
      <Card
        title="Model comparison"
        subtitle="Generate forecasts with different models for the same product and location"
      >
        {comparisons.length ? (
          <Table
            headers={[
              "Model",
              "Horizon",
              "Demand",
              "MAE",
              "WAPE",
              "Confidence",
            ]}
          >
            {comparisons.map((f, i) => (
              <tr key={i}>
                <td>{f.model_name.replaceAll("_", " ")}</td>
                <td>{f.horizon}d</td>
                <td>{number(f.predicted_demand)}</td>
                <td>{number(f.mae)}</td>
                <td>{number(f.wape * 100)}%</td>
                <td>{number(f.confidence_score * 100)}%</td>
              </tr>
            ))}
          </Table>
        ) : (
          <Empty text="Run different models to compare their observed holdout errors." />
        )}
      </Card>
    </>
  );
}
