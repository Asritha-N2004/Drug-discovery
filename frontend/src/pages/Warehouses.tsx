import { ArrowUpRight, MapPin, Warehouse } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { number, useData } from "../api";
import { Badge, Card, Drawer, Metric, Progress, Table } from "../components";
import type { InventoryRow, Location, Page, Transfer } from "../types";
export default function Warehouses() {
  const locations = useData<Location[]>("/api/locations");
  const transfers = useData<Transfer[]>("/api/transfers");
  const orders = useData<
    {
      id: number;
      location_id: number;
      product_id: number;
      quantity: number;
      status: string;
      expected_date: string;
    }[]
  >("/api/purchase-orders");
  const [selected, setSelected] = useState<Location | null>(null);
  const inventory = useData<Page<InventoryRow>>(
    `/api/inventory?location_id=${selected?.id}&page_size=200`,
    !!selected,
  );
  const sources = locations.data?.filter((l) =>
    ["warehouse", "distribution_center", "online"].includes(l.location_type),
  );
  return (
    <>
      <div className="metrics">
        <Metric label="Supply facilities" value={number(sources?.length)} />
        <Metric
          label="Supply units"
          value={number(sources?.reduce((s, l) => s + l.on_hand, 0))}
        />
        <Metric
          label="Scheduled transfers"
          value={number(
            transfers.data?.filter((t) => t.status === "scheduled").length,
          )}
        />
        <Metric
          label="Incoming purchase orders"
          value={number(
            orders.data?.filter((o) => o.status === "pending").length,
          )}
        />
      </div>
      <div className="agent-grid">
        {sources?.map((l) => (
          <Card key={l.id}>
            <div className="agent-top">
              <div className="agent-icon">
                <Warehouse />
              </div>
              <Badge value={l.location_type} />
            </div>
            <h3>{l.location_name}</h3>
            <p>
              <MapPin size={13} /> {l.region}
            </p>
            <div className="warehouse-total">
              {number(l.on_hand)} <small>units on hand</small>
            </div>
            <Progress value={l.utilization} />
            <div className="agent-meta">
              <span>
                Storage capacity<strong>{number(l.storage_capacity)}</strong>
              </span>
              <span>
                Fulfillment / run
                <strong>{number(l.fulfillment_capacity)}</strong>
              </span>
            </div>
            <button onClick={() => setSelected(l)}>
              Inspect inventory <ArrowUpRight size={15} />
            </button>
          </Card>
        ))}
      </div>
      <Card
        title="Incoming replenishment"
        subtitle="Synthetic supplier purchase orders"
      >
        <Table
          headers={[
            "Order",
            "Location",
            "Product ID",
            "Quantity",
            "Expected",
            "Status",
          ]}
        >
          {orders.data?.map((o) => (
            <tr key={o.id}>
              <td>PO-{String(o.id).padStart(4, "0")}</td>
              <td>
                {
                  locations.data?.find((l) => l.id === o.location_id)
                    ?.location_name
                }
              </td>
              <td>{o.product_id}</td>
              <td>{number(o.quantity)}</td>
              <td>{o.expected_date}</td>
              <td>
                <Badge value={o.status} />
              </td>
            </tr>
          ))}
        </Table>
      </Card>
      <p className="note">
        Demand-based warehouse-to-channel replenishment recommendations are
        generated in <Link to="/allocation">Inventory allocation</Link>.
        Inter-warehouse movements can be proposed in Logistics & transfers.
      </p>
      {selected && (
        <Drawer
          title={selected.location_name}
          onClose={() => setSelected(null)}
        >
          <Progress value={selected.utilization} />
          <Table headers={["Product", "Available", "Safety", "Status"]}>
            {inventory.data?.items.map((i) => (
              <tr key={i.id}>
                <td>{i.product_name}</td>
                <td>{i.quantity_available}</td>
                <td>{i.safety_stock}</td>
                <td>
                  <Badge value={i.status} />
                </td>
              </tr>
            ))}
          </Table>
        </Drawer>
      )}
    </>
  );
}
