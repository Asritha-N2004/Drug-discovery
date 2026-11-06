import { ChevronRight, Download, Plus, Search } from "lucide-react";
import { useContext, useState } from "react";
import { api, errorText, number, useData } from "../api";
import {
  Badge,
  Card,
  Drawer,
  Empty,
  ErrorBox,
  Loading,
  Table,
} from "../components";
import { Auth, useAction } from "../context";
import type { InventoryRow, Page } from "../types";
export default function Inventory() {
  const { canOperate, canManage } = useContext(Auth);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("sku");
  const [detail, setDetail] = useState<InventoryRow | null>(null);
  const [create, setCreate] = useState(false);
  const data = useData<Page<InventoryRow>>(
    `/api/inventory?search=${encodeURIComponent(search)}&status=${status}&location_type=${type}&category=${encodeURIComponent(category)}&page_no=${page}&sort=${sort}`,
  );
  const all = useData<InventoryRow[]>(
    `/api/inventory/${detail?.product_id}`,
    !!detail,
  );
  const update = useAction<{ id: number; body: Record<string, number> }>(
    (v) => api.put(`/api/inventory/${v.id}`, v.body),
    "Inventory updated and audited",
  );
  const add = useAction<Record<string, unknown>>(
    (v) => api.post("/api/products", v),
    "Product created",
  );
  return (
    <>
      <Card
        title="Inventory ledger"
        subtitle={`${number(data.data?.total)} records · reservations protected`}
        action={
          <div className="button-row">
            <button
              onClick={async () => {
                try {
                  const r = await api.get("/api/reports/export", {
                    responseType: "blob",
                  });
                  const a = document.createElement("a");
                  a.href = URL.createObjectURL(r.data);
                  a.download = "inventory.csv";
                  a.click();
                  URL.revokeObjectURL(a.href);
                } catch (e) {
                  alert(errorText(e));
                }
              }}
            >
              <Download size={16} />
              Export CSV
            </button>
            {canManage && (
              <button className="primary" onClick={() => setCreate(true)}>
                <Plus size={16} />
                Add product
              </button>
            )}
          </div>
        }
      >
        <div className="filters">
          <div className="search">
            <Search size={17} />
            <input
              aria-label="Search inventory"
              placeholder="Search product or SKU…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <select
            aria-label="Stock status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            {["healthy", "low", "stockout", "overstock"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
          <select
            aria-label="Location type"
            value={type}
            onChange={(e) => {
              setType(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All locations</option>
            {["warehouse", "store", "online", "distribution_center"].map(
              (x) => (
                <option key={x}>{x}</option>
              ),
            )}
          </select>
          <select
            aria-label="Category"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All categories</option>
            {[
              "Electronics",
              "Clothing",
              "Grocery",
              "Home Appliances",
              "Personal Care",
              "Accessories",
            ].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
          <select
            aria-label="Sort inventory"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="sku">Sort: SKU</option>
            <option value="quantity_available">Available stock</option>
            <option value="product_name">Product name</option>
            <option value="location_name">Location</option>
          </select>
        </div>
        {data.error && <ErrorBox message={errorText(data.error)} />}{" "}
        {data.isPending ? (
          <Loading />
        ) : (
          <Table
            headers={[
              "Product / SKU",
              "Category",
              "Location",
              "On hand",
              "Reserved",
              "Available",
              "Safety",
              "Status",
              "",
            ]}
          >
            {data.data?.items.map((r) => (
              <tr key={r.id}>
                <td>
                  <strong>{r.product_name}</strong>
                  <small>{r.sku}</small>
                </td>
                <td>{r.category}</td>
                <td>
                  {r.location_name}
                  <small>{r.location_type.replaceAll("_", " ")}</small>
                </td>
                <td>{number(r.quantity_on_hand)}</td>
                <td>{r.quantity_reserved}</td>
                <td>
                  <strong>{r.quantity_available}</strong>
                </td>
                <td>{r.safety_stock}</td>
                <td>
                  <Badge value={r.status} />
                </td>
                <td>
                  <button
                    aria-label={`View ${r.sku} at ${r.location_name}`}
                    className="icon-button"
                    onClick={() => {
                      setDetail(r);
                      update.reset();
                    }}
                  >
                    <ChevronRight size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </Table>
        )}
        {!data.isPending && !data.data?.items.length && (
          <Empty text="No inventory matches these filters." />
        )}
        <div className="pagination">
          <span>
            Page {page} · {number(data.data?.total)} records
          </span>
          <button disabled={page === 1} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <button
            disabled={page * 25 >= (data.data?.total || 0)}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      </Card>
      {detail && (
        <Drawer title={detail.product_name} onClose={() => setDetail(null)}>
          <Badge value={detail.status} />
          <p>
            {detail.sku} · {detail.category}
          </p>
          <h3>{detail.location_name}</h3>
          <form
            key={`${detail.id}-${detail.version}`}
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              update.mutate(
                {
                  id: detail.id,
                  body: {
                    quantity_on_hand: Number(f.get("quantity_on_hand")),
                    quantity_reserved: Number(f.get("quantity_reserved")),
                    safety_stock: Number(f.get("safety_stock")),
                    reorder_level: Number(f.get("reorder_level")),
                    version: detail.version,
                  },
                },
                { onSuccess: () => setDetail(null) },
              );
            }}
          >
            {(
              [
                "quantity_on_hand",
                "quantity_reserved",
                "safety_stock",
                "reorder_level",
              ] as const
            ).map((k) => (
              <label key={k}>
                {k.replaceAll("_", " ")}
                <input
                  name={k}
                  type="number"
                  min="0"
                  defaultValue={detail[k]}
                  required
                  disabled={!canOperate}
                />
              </label>
            ))}
            {update.error && <ErrorBox message={errorText(update.error)} />}{" "}
            {canOperate && (
              <button className="primary" disabled={update.isPending}>
                Save inventory adjustment
              </button>
            )}
          </form>
          <h3>Availability across locations</h3>
          <Table headers={["Location", "Available"]}>
            {all.data?.map((i) => (
              <tr key={i.id}>
                <td>{i.location_name}</td>
                <td>{i.quantity_available}</td>
              </tr>
            ))}
          </Table>
        </Drawer>
      )}
      {create && (
        <Drawer title="Add a product" onClose={() => setCreate(false)}>
          <form
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              add.mutate(
                {
                  sku: f.get("sku"),
                  product_name: f.get("product_name"),
                  category: f.get("category"),
                  unit_cost: Number(f.get("unit_cost")),
                  selling_price: Number(f.get("selling_price")),
                },
                { onSuccess: () => setCreate(false) },
              );
            }}
          >
            {[
              "sku",
              "product_name",
              "category",
              "unit_cost",
              "selling_price",
            ].map((k) => (
              <label key={k}>
                {k.replaceAll("_", " ")}
                <input
                  name={k}
                  type={
                    k.includes("cost") || k.includes("price")
                      ? "number"
                      : "text"
                  }
                  min="0"
                  step="0.01"
                  required
                />
              </label>
            ))}
            {add.error && <ErrorBox message={errorText(add.error)} />}
            <button className="primary" disabled={add.isPending}>
              Create product
            </button>
            <small>
              New products receive zero-stock records at each active location.
              Enter starting stock with an authorized inventory adjustment.
            </small>
          </form>
        </Drawer>
      )}
    </>
  );
}
