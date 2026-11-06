import {
  Activity,
  ArrowUpRight,
  ChevronRight,
  Network,
  Play,
} from "lucide-react";
import React, { useContext, useState } from "react";
import { api, errorText, useData } from "../api";
import { Badge, Card, Drawer, Empty, ErrorBox } from "../components";
import { Auth, useAction } from "../context";
import type { Agent, Execution } from "../types";
export default function Agents() {
  const { canManage } = useContext(Auth);
  const agents = useData<Agent[]>("/api/agents");
  const logs = useData<{
    executions: Execution[];
    messages: {
      id: number;
      sender: string;
      recipient: string;
      payload: Record<string, unknown>;
      timestamp: string;
    }[];
  }>("/api/agents/logs");
  const run = useAction<string | undefined>(
    (id) =>
      api.post("/api/agents/run", {
        agent_id: id,
        run_name: id ? `${id} diagnostic workflow` : "Full agent workflow",
      }),
    "Agent workflow started",
  );
  const [detail, setDetail] = useState<Agent | null>(null);
  return (
    <>
      <div className="section-toolbar">
        <div className="inline-status">
          <span className="live-dot" />
          10 deterministic agents · structured message bus
        </div>
        {canManage && (
          <button
            className="primary"
            disabled={
              run.isPending || agents.data?.some((a) => a.status === "running")
            }
            onClick={() => run.mutate(undefined)}
          >
            <Play size={16} />
            Run all agents
          </button>
        )}
      </div>
      {run.error && <ErrorBox message={errorText(run.error)} />}
      <Card
        title="Coordinated workflow"
        subtitle="Snapshot → forecast → recommendations → optimization → validation → human approval"
      >
        <div className="workflow">
          {[
            "Supervisor",
            "Forecast",
            "Channels",
            "Warehouse",
            "Risk",
            "Allocation",
            "Logistics",
            "Approval",
          ].map((s, i) => (
            <React.Fragment key={s}>
              <div>
                <span>{String(i + 1).padStart(2, "0")}</span>
                {s}
              </div>
              {i < 7 && <ChevronRight size={16} />}
            </React.Fragment>
          ))}
        </div>
      </Card>
      {agents.error && <ErrorBox message={errorText(agents.error)} />}
      <div className="agent-grid">
        {agents.data?.map((a, i) => (
          <Card key={a.id}>
            <div className="agent-top">
              <div className={`agent-icon color-${i % 3}`}>
                <Network size={23} />
              </div>
              <Badge value={a.status} />
            </div>
            <h3>{a.name}</h3>
            <p className="agent-role">{a.role}</p>
            <div className="agent-meta">
              <span>
                Tasks completed<strong>{a.tasks_completed}</strong>
              </span>
              <span>
                Last execution
                <strong>
                  {a.last_execution
                    ? new Date(a.last_execution.created_at).toLocaleTimeString()
                    : "Not run"}
                </strong>
              </span>
            </div>
            <div className="agent-output">
              {a.last_execution?.error_message ||
                (a.last_execution
                  ? Object.entries(a.last_execution.output_summary)
                      .slice(0, 2)
                      .map(
                        ([k, v]) =>
                          `${k.replaceAll("_", " ")}: ${typeof v === "object" ? "structured data" : v}`,
                      )
                      .join(" · ")
                  : "Ready to receive a workflow task.")}
            </div>
            <div className="button-row">
              <button onClick={() => setDetail(a)}>
                View output <ArrowUpRight size={14} />
              </button>
              {canManage && (
                <button
                  disabled={run.isPending}
                  onClick={() => run.mutate(a.id)}
                >
                  <Play size={13} />
                  Run
                </button>
              )}
            </div>
          </Card>
        ))}
      </div>
      <p className="note">
        Individual execution runs the selected agent within the dependency
        workflow, ensuring its inputs are current and auditable.
      </p>
      <div className="grid-two">
        <Card
          title="Execution timeline"
          subtitle="Persisted agent status and duration"
        >
          <div className="timeline scroll-area">
            {logs.data?.executions.slice(0, 20).map((e) => (
              <div key={e.id}>
                <div className="timeline-dot">
                  <Activity size={14} />
                </div>
                <div>
                  <strong>
                    {e.agent_name} <Badge value={e.status} />
                  </strong>
                  <p>
                    {e.error_message ||
                      `${e.execution_duration}s · workflow ${e.execution_id.slice(0, 8)}`}
                  </p>
                  <small>{new Date(e.created_at).toLocaleString()}</small>
                </div>
              </div>
            ))}
            {!logs.data?.executions.length && <Empty />}
          </div>
        </Card>
        <Card
          title="Agent communications"
          subtitle="Structured recommendations delivered to the supervisor"
        >
          <div className="scroll-area">
            {logs.data?.messages.slice(0, 10).map((m) => (
              <div className="message" key={m.id}>
                <strong>
                  {m.sender} <span>→</span> {m.recipient}
                </strong>
                <pre>{JSON.stringify(m.payload, null, 2)}</pre>
              </div>
            ))}
            {!logs.data?.messages.length && <Empty />}
          </div>
        </Card>
      </div>
      {detail && (
        <Drawer title={detail.name} onClose={() => setDetail(null)}>
          <p>{detail.role}</p>
          {detail.last_execution ? (
            <>
              <Badge value={detail.last_execution.status} />
              <h3>Input</h3>
              <pre>
                {JSON.stringify(detail.last_execution.input_summary, null, 2)}
              </pre>
              <h3>Output</h3>
              <pre>
                {JSON.stringify(detail.last_execution.output_summary, null, 2)}
              </pre>
              <p>
                Decision confidence:{" "}
                {detail.last_execution.confidence ?? "Not applicable"}
              </p>
            </>
          ) : (
            <Empty />
          )}
        </Drawer>
      )}
    </>
  );
}
