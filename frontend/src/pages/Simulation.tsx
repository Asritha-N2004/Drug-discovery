import { Download, FlaskConical, Play } from "lucide-react";
import { useContext, useState } from "react";
import { api, csvDownload, errorText, money, number, useData } from "../api";
import {
  Badge,
  Bars,
  Card,
  Empty,
  ErrorBox,
  Metric,
  Table,
} from "../components";
import { scenarios } from "../config";
import { Auth, useAction } from "../context";
import type { Sim } from "../types";
export default function Simulation() {
  const { canManage } = useContext(Auth);
  const [scenario, setScenario] = useState("online_surge");
  const [multiplier, setMultiplier] = useState(2);
  const [selected, setSelected] = useState<Sim | null>(null);
  const sims = useData<Sim[]>("/api/simulation/runs");
  const run = useAction<void>(async () => {
    const r = await api.post("/api/simulation/run", { scenario, multiplier });
    setSelected(r.data);
  }, "Sandbox simulation completed. Live inventory unchanged.");
  const s = selected?.results;
  return (
    <>
      <div className="sandbox-banner">
        <FlaskConical />
        <div>
          <strong>A safe space for what-if decisions.</strong>
          <p>
            Simulations use a copy of current stock. No live inventory,
            transfers or allocation approvals are changed.
          </p>
        </div>
        <Badge value="isolated sandbox" />
      </div>
      <Card
        title="Scenario configuration"
        subtitle="Stress-test the network with reproducible demand and supply shocks"
      >
        <div className="filters">
          <label>
            Scenario
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
            >
              {Object.entries(scenarios).map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Shock multiplier
            <input
              aria-label="Shock multiplier"
              type="number"
              step="0.1"
              min="1"
              max="5"
              value={multiplier}
              onChange={(e) => setMultiplier(+e.target.value)}
            />
          </label>
          {canManage && (
            <button
              className="primary"
              disabled={run.isPending || multiplier < 1 || multiplier > 5}
              onClick={() => run.mutate()}
            >
              <Play size={16} />
              {run.isPending ? "Simulating…" : "Run simulation"}
            </button>
          )}
        </div>
        {run.error && <ErrorBox message={errorText(run.error)} />}
      </Card>
      {s && (
        <>
          <div className="metrics">
            <Metric
              label="Initial inventory"
              value={number(s.initial_inventory)}
              detail={`${number(s.scenario_inventory)} after supply shock`}
            />
            <Metric
              label="Simulated demand"
              value={number(s.simulated_demand)}
            />
            <Metric
              label="Shortage reduction"
              value={`${number(s.stockout_reduction)}%`}
            />
            <Metric
              label="Modeled cost avoidance"
              value={money(s.estimated_savings)}
            />
          </div>
          <div className="grid-two">
            <Card
              title="Baseline vs optimized"
              subtitle="Unmet demand in integer units"
            >
              <Bars
                data={[
                  {
                    name: "Unmet demand",
                    baseline: s.baseline_shortage,
                    optimized: s.optimized_shortage,
                  },
                ]}
                keys={["baseline", "optimized"]}
              />
            </Card>
            <Card
              title="Cost comparison"
              subtitle="Shortage penalties + modeled movement and holding costs"
            >
              <Bars
                data={[
                  {
                    name: "Operational cost (INR)",
                    baseline: s.baseline_cost,
                    optimized: s.optimized_cost,
                  },
                ]}
                keys={["baseline", "optimized"]}
              />
            </Card>
          </div>
          <Card
            title="Agent scenario decisions"
            subtitle={`${number(s.total_allocated)} units recommended · sandbox only`}
          >
            <pre>{JSON.stringify(s.agent_decisions, null, 2)}</pre>
            <button
              onClick={() =>
                csvDownload(
                  s.recommendations as unknown as Record<string, unknown>[],
                  "simulation-allocation.csv",
                )
              }
            >
              <Download size={16} />
              Export simulated allocation
            </button>
          </Card>
        </>
      )}
      <Card title="Simulation history" subtitle="Saved scenario results">
        <Table
          headers={["Scenario", "Created", "Demand", "Shortage reduction", ""]}
        >
          {sims.data?.map((s) => (
            <tr key={s.id}>
              <td>{scenarios[s.scenario]}</td>
              <td>{new Date(s.created_at).toLocaleString()}</td>
              <td>{number(s.results.simulated_demand)}</td>
              <td>{number(s.results.stockout_reduction)}%</td>
              <td>
                <button onClick={() => setSelected(s)}>View results</button>
              </td>
            </tr>
          ))}
        </Table>
        {!sims.data?.length && (
          <Empty text="Choose a scenario to compare baseline and optimized outcomes." />
        )}
      </Card>
    </>
  );
}
