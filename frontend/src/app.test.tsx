// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
import {
  Agents,
  Allocation,
  App,
  Auth,
  Dashboard,
  Forecasting,
  Inventory,
  Simulation,
} from "./main";
import type { Summary } from "./types";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  AreaChart: () => null,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  BarChart: () => null,
  Bar: () => null,
  Legend: () => null,
}));
const summary: Summary = {
  total_products: 100,
  total_inventory: 12345,
  total_warehouses: 6,
  total_stores: 15,
  online_inventory: 1000,
  offline_inventory: 2000,
  low_stock: 23,
  overstock: 100,
  stockout_risk: 1.5,
  inventory_turnover: 4.2,
  forecast_accuracy: null,
  estimated_savings: 0,
  inventory_value: 200000,
};
const row = {
  id: 1,
  product_id: 1,
  location_id: 1,
  sku: "RTL-0001",
  product_name: "Wireless Headphones",
  category: "Electronics",
  location_name: "Mumbai Warehouse",
  location_type: "warehouse",
  quantity_on_hand: 25,
  quantity_reserved: 3,
  quantity_available: 22,
  safety_stock: 10,
  reorder_level: 30,
  version: 1,
  status: "low",
};
const run = {
  id: "run-1",
  run_name: "Test network plan",
  status: "waiting_for_approval",
  total_allocated: 10,
  total_cost: 100,
  objective_value: 200,
  stockout_risk: 0.1,
  created_at: "2026-11-06T12:00:00Z",
  results: {
    stockout_reduction: 90,
    baseline_shortage: 100,
    optimized_shortage: 10,
    estimated_savings: 1000,
    solver: ["scipy_milp"],
  },
};
function view(node: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      <MemoryRouter>
        <Auth.Provider
          value={{
            user: {
              id: 1,
              name: "Admin",
              email: "admin@retail.local",
              role: "Administrator",
            },
            canManage: true,
            canOperate: true,
          }}
        >
          {node}
        </Auth.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  sessionStorage.clear();
  vi.spyOn(api, "get").mockImplementation(async (path) => {
    const p = String(path);
    let data: unknown = [];
    if (p.includes("summary")) data = summary;
    else if (p === "/api/dashboard/inventory-health")
      data = { statuses: [], locations: [] };
    else if (p === "/api/agents/logs") data = { executions: [], messages: [] };
    else if (p === "/api/agents")
      data = [
        {
          id: "demand",
          name: "Demand Forecasting",
          role: "Forecast demand",
          status: "idle",
          tasks_completed: 0,
          last_execution: null,
        },
      ];
    else if (p.startsWith("/api/inventory?"))
      data = { items: [row], total: 1, page: 1, page_size: 25 };
    else if (p.startsWith("/api/products?"))
      data = {
        items: [
          { id: 1, sku: "RTL-0001", product_name: "Wireless Headphones" },
        ],
        total: 1,
      };
    else if (p === "/api/locations")
      data = [
        { id: 21, location_name: "Online Center", location_type: "online" },
      ];
    else if (p === "/api/optimization/runs") data = [run];
    else if (p.includes("/recommendations"))
      data = [
        {
          id: 1,
          product_name: "Wireless Headphones",
          sku: "RTL-0001",
          source: "Warehouse",
          destination: "Store",
          sales_channel: "offline",
          allocated_quantity: 10,
          estimated_cost: 100,
          before: 2,
          after: 12,
          reason: "Demand replenishment",
          eta_hours: 4,
        },
      ];
    else if (p.includes("/api/optimization/runs/")) data = run;
    return { data } as never;
  });
  vi.spyOn(api, "post").mockResolvedValue({
    data: { id: "run-1", items: [] },
  } as never);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
describe("connected application workflows", () => {
  it("shows login and submits credentials", async () => {
    view(<App />);
    fireEvent.change(await screen.findByLabelText("Password"), {
      target: { value: "test" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /Sign in to workspace/ }),
    );
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/api/auth/login", {
        email: "admin@retail.local",
        password: "test",
      }),
    );
  });
  it("renders backend dashboard metrics", async () => {
    view(<Dashboard />);
    await screen.findAllByText("12,345");
    expect(screen.getByText("Stock health alerts")).toBeTruthy();
    expect(api.get).toHaveBeenCalledWith("/api/dashboard/summary");
  });
  it("filters inventory through the API", async () => {
    view(<Inventory />);
    await screen.findByText("Wireless Headphones");
    fireEvent.change(screen.getByLabelText("Search inventory"), {
      target: { value: "coffee" },
    });
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining("search=coffee"),
      ),
    );
    fireEvent.change(screen.getByLabelText("Stock status"), {
      target: { value: "low" },
    });
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining("status=low"),
      ),
    );
  });
  it("starts real agent workflows", async () => {
    view(<Agents />);
    await screen.findByText("Demand Forecasting");
    fireEvent.click(screen.getByRole("button", { name: "Run all agents" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        "/api/agents/run",
        expect.objectContaining({ run_name: "Full agent workflow" }),
      ),
    );
  });
  it("submits selected forecast configuration", async () => {
    view(<Forecasting />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Generate forecast" }),
    );
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/api/forecast/run", {
        product_id: 1,
        location_id: 21,
        model: "exponential_smoothing",
        horizon: 7,
      }),
    );
  });
  it("requires explicit confirmation before allocation approval", async () => {
    view(<Allocation />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Approve allocation" }),
    );
    expect(api.post).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Confirm approve" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(
        "/api/optimization/runs/run-1/approve",
      ),
    );
  });
  it("runs a sandbox scenario through the API", async () => {
    view(<Simulation />);
    fireEvent.change(screen.getByLabelText("Shock multiplier"), {
      target: { value: "3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run simulation" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/api/simulation/run", {
        scenario: "online_surge",
        multiplier: 3,
      }),
    );
  });
});
