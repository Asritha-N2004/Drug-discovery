import { useContext } from "react";
import { api, errorText, useData } from "../api";
import { Badge, Card, ErrorBox, Table } from "../components";
import { models } from "../config";
import { Auth, useAction } from "../context";
export default function SettingsPage() {
  const { user, canManage } = useContext(Auth);
  const settings = useData<{
    optimization: Record<string, number>;
    forecast: { model: string; horizon: number };
    notifications: { inventory_alerts: boolean; workflow_updates: boolean };
  }>("/api/settings");
  const health = useData<Record<string, string>>("/health");
  const users = useData<
    { id: number; name: string; email: string; role: string; role_id: number }[]
  >("/api/users", user.role === "Administrator");
  const audits = useData<
    {
      id: number;
      action: string;
      entity_type: string;
      entity_id: string;
      timestamp: string;
    }[]
  >("/api/audit", canManage);
  const save = useAction<Record<string, number>>(
    (v) => api.put("/api/settings/optimization", v),
    "Optimization settings saved",
  );
  const profile = useAction<string>(
    (name) => api.put("/api/auth/me", { name }),
    "Profile updated",
  );
  const role = useAction<{ id: number; role_id: number }>(
    (v) => api.put(`/api/users/${v.id}/role`, { role_id: v.role_id }),
    "Role updated",
  );
  const forecast = useAction<{ model: string; horizon: number }>(
    (v) => api.put("/api/settings/forecast", v),
    "Forecast defaults saved",
  );
  const preferences = useAction<{
    inventory_alerts: boolean;
    workflow_updates: boolean;
  }>(
    (v) => api.put("/api/settings/notifications", v),
    "Notification preferences saved",
  );
  return (
    <>
      <div className="grid-two">
        <Card title="Your profile" subtitle={user.email}>
          <form
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              profile.mutate(String(new FormData(e.currentTarget).get("name")));
            }}
          >
            <label>
              Display name
              <input name="name" defaultValue={user.name} required />
            </label>
            <label>
              Role
              <input value={user.role} disabled />
            </label>
            <button disabled={profile.isPending}>Save profile</button>
          </form>
        </Card>
        <Card
          title="System health"
          subtitle="Live API and database connectivity"
        >
          <div className="health-list">
            {Object.entries(health.data || {}).map(([k, v]) => (
              <div key={k}>
                <span>{k.replaceAll("_", " ")}</span>
                <Badge value={v} />
              </div>
            ))}
          </div>
          <p className="note">
            Single-process local coordinator. Event streaming uses WebSockets
            with 15-second API polling fallback.
          </p>
        </Card>
        <Card
          title="Optimization & safety stock"
          subtitle="Weights apply to subsequent allocation runs"
        >
          {settings.data && (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                save.mutate(
                  Object.fromEntries(
                    Object.keys(settings.data!.optimization).map((k) => [
                      k,
                      Number(f.get(k)),
                    ]),
                  ),
                );
              }}
            >
              {Object.entries(settings.data.optimization).map(([k, v]) => (
                <label key={k}>
                  {k.replaceAll("_", " ")}
                  <input
                    name={k}
                    type="number"
                    step="0.1"
                    min={
                      k === "safety_stock_multiplier"
                        ? 1
                        : k === "online_priority"
                          ? 0.1
                          : k === "stockout_penalty"
                            ? 1
                            : 0
                    }
                    max={
                      k === "stockout_penalty"
                        ? 1000
                        : k === "holding_cost"
                          ? 100
                          : 5
                    }
                    defaultValue={v}
                    disabled={!canManage}
                    required
                  />
                </label>
              ))}
              {save.error && <ErrorBox message={errorText(save.error)} />}{" "}
              {canManage && (
                <button className="primary" disabled={save.isPending}>
                  Save optimization settings
                </button>
              )}
            </form>
          )}
        </Card>
        <Card
          title="Forecasting defaults"
          subtitle="Local models with no external AI dependency"
        >
          {settings.data && (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                forecast.mutate({
                  model: String(f.get("model")),
                  horizon: Number(f.get("horizon")),
                });
              }}
            >
              <label>
                Default model
                <select
                  name="model"
                  defaultValue={settings.data.forecast.model}
                  disabled={!canManage}
                >
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
                  name="horizon"
                  type="number"
                  min="1"
                  max="90"
                  defaultValue={settings.data.forecast.horizon}
                  disabled={!canManage}
                />
              </label>
              {canManage && (
                <button disabled={forecast.isPending}>
                  Save forecast defaults
                </button>
              )}
              {forecast.error && (
                <ErrorBox message={errorText(forecast.error)} />
              )}
            </form>
          )}
          <p className="note">
            Safety stock, reservations and storage capacity are enforced on
            every approved movement. Price recommendations remain suggestions.
          </p>
        </Card>
        <Card
          title="Notification preferences"
          subtitle="Personal in-app notification filters"
        >
          {settings.data && (
            <form
              className="form-stack"
              key={JSON.stringify(settings.data.notifications)}
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                preferences.mutate({
                  inventory_alerts: f.get("inventory_alerts") === "on",
                  workflow_updates: f.get("workflow_updates") === "on",
                });
              }}
            >
              <label>
                <span>
                  <input
                    type="checkbox"
                    name="inventory_alerts"
                    defaultChecked={
                      settings.data.notifications.inventory_alerts
                    }
                  />{" "}
                  Inventory alerts
                </span>
              </label>
              <label>
                <span>
                  <input
                    type="checkbox"
                    name="workflow_updates"
                    defaultChecked={
                      settings.data.notifications.workflow_updates
                    }
                  />{" "}
                  Workflow updates
                </span>
              </label>
              <button disabled={preferences.isPending}>
                Save notification preferences
              </button>
            </form>
          )}
        </Card>
      </div>
      {user.role === "Administrator" && (
        <Card
          title="Team & roles"
          subtitle="Changes require an administrator account"
        >
          {role.error && <ErrorBox message={errorText(role.error)} />}
          <Table headers={["Name", "Email", "Role"]}>
            {users.data?.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>
                  <select
                    aria-label={`Role for ${u.email}`}
                    value={u.role_id}
                    disabled={u.id === user.id || role.isPending}
                    onChange={(e) =>
                      role.mutate({ id: u.id, role_id: +e.target.value })
                    }
                  >
                    {[
                      "Administrator",
                      "Inventory Manager",
                      "Warehouse Manager",
                      "Store Manager",
                      "Analyst",
                    ].map((r, i) => (
                      <option key={r} value={i + 1}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </Table>
        </Card>
      )}
      {canManage && (
        <Card
          title="Audit trail"
          subtitle="Inventory, approval and configuration changes"
        >
          <Table headers={["Action", "Entity", "ID", "Timestamp"]}>
            {audits.data?.map((a) => (
              <tr key={a.id}>
                <td>
                  <Badge value={a.action} />
                </td>
                <td>{a.entity_type}</td>
                <td>{a.entity_id.slice(0, 12)}</td>
                <td>{new Date(a.timestamp).toLocaleString()}</td>
              </tr>
            ))}
          </Table>
        </Card>
      )}
    </>
  );
}
