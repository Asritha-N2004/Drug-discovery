import { Plus, Truck } from "lucide-react";
import { useContext, useState } from "react";
import { api, errorText, money, number, useData } from "../api";
import {
  Badge,
  Card,
  Drawer,
  Empty,
  ErrorBox,
  Metric,
  Table,
} from "../components";
import { Auth, useAction } from "../context";
import type { Location, Page, Product, Transfer } from "../types";
export default function Transfers() {
  const { canOperate } = useContext(Auth);
  const transfers = useData<Transfer[]>("/api/transfers");
  const locations = useData<Location[]>("/api/locations");
  const products = useData<Page<Product>>("/api/products?page_size=200");
  const [create, setCreate] = useState(false);
  const update = useAction<{ id: number; status: string }>(
    (v) => api.put(`/api/transfers/${v.id}/status`, { status: v.status }),
    "Transfer tracking updated",
  );
  const propose = useAction<Record<string, number>>(
    (v) => api.post("/api/transfers", v),
    "Transfer proposed. Review and approve it in Inventory allocation.",
  );
  return (
    <>
      <div className="metrics">
        {["scheduled", "in_transit", "delivered", "reversed"].map((s) => (
          <Metric
            key={s}
            label={s.replaceAll("_", " ")}
            value={number(transfers.data?.filter((t) => t.status === s).length)}
            icon={<Truck size={17} />}
          />
        ))}
      </div>
      <Card
        title="Transfer tracking"
        subtitle="Inventory is posted at allocation approval; tracking updates do not post stock again."
        action={
          canOperate && (
            <button className="primary" onClick={() => setCreate(true)}>
              <Plus size={16} />
              Propose transfer
            </button>
          )
        }
      >
        {update.error && <ErrorBox message={errorText(update.error)} />}{" "}
        {transfers.data?.length ? (
          <Table
            headers={[
              "Transfer / product",
              "Route",
              "Quantity",
              "ETA",
              "Cost",
              "Status",
              "Next step",
            ]}
          >
            {transfers.data.map((t) => (
              <tr key={t.id}>
                <td>
                  <strong>TR-{String(t.id).padStart(5, "0")}</strong>
                  <small>{t.product_name}</small>
                </td>
                <td>
                  {t.source}
                  <small>→ {t.destination}</small>
                </td>
                <td>{t.quantity}</td>
                <td>{t.eta_hours}h modeled</td>
                <td>{money(t.estimated_cost)}</td>
                <td>
                  <Badge value={t.status} />
                </td>
                <td>
                  {canOperate &&
                    ["scheduled", "in_transit"].includes(t.status) && (
                      <button
                        disabled={update.isPending}
                        onClick={() =>
                          update.mutate({
                            id: t.id,
                            status:
                              t.status === "scheduled"
                                ? "in_transit"
                                : "delivered",
                          })
                        }
                      >
                        {t.status === "scheduled"
                          ? "Dispatch"
                          : "Mark delivered"}
                      </button>
                    )}
                </td>
              </tr>
            ))}
          </Table>
        ) : (
          <Empty text="Approve an allocation to create tracked inventory transfers." />
        )}
      </Card>
      {create && (
        <Drawer
          title="Propose inventory transfer"
          onClose={() => setCreate(false)}
        >
          <form
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              propose.mutate(
                {
                  product_id: Number(f.get("product_id")),
                  source_location_id: Number(f.get("source")),
                  destination_location_id: Number(f.get("destination")),
                  quantity: Number(f.get("quantity")),
                },
                { onSuccess: () => setCreate(false) },
              );
            }}
          >
            <label>
              Product
              <select name="product_id">
                {products.data?.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.sku} · {p.product_name}
                  </option>
                ))}
              </select>
            </label>
            {["source", "destination"].map((k) => (
              <label key={k}>
                {k}
                <select name={k}>
                  {locations.data?.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.location_name}
                    </option>
                  ))}
                </select>
              </label>
            ))}
            <label>
              Quantity
              <input
                name="quantity"
                type="number"
                min="1"
                defaultValue="10"
                required
              />
            </label>
            {propose.error && <ErrorBox message={errorText(propose.error)} />}
            <p>
              This creates a proposal. An inventory manager must approve the
              movement.
            </p>
            <button className="primary" disabled={propose.isPending}>
              Create proposal
            </button>
          </form>
        </Drawer>
      )}
    </>
  );
}
