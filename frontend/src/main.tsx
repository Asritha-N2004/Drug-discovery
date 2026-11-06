import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ArrowLeftRight,
  ArrowUpRight,
  Bell,
  ChartNoAxesCombined,
  ChartPie,
  Check,
  ChevronDown,
  ChevronRight,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  Menu,
  Network,
  Package,
  Settings,
  Truck,
  Warehouse,
} from "lucide-react";
import React, { useContext, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { api, errorText, useData } from "./api";
import { Badge, Drawer, Empty, ErrorBox, Loading } from "./components";
import { Auth, Toast, useAction } from "./context";
import Agents from "./pages/Agents";
import Allocation from "./pages/Allocation";
import Analytics from "./pages/Analytics";
import Dashboard from "./pages/Dashboard";
import Forecasting from "./pages/Forecasting";
import Inventory from "./pages/Inventory";
import SettingsPage from "./pages/SettingsPage";
import Simulation from "./pages/Simulation";
import Transfers from "./pages/Transfers";
import Warehouses from "./pages/Warehouses";
import "./styles.css";
import type { Notification, User } from "./types";

const client = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
});
const nav = [
  ["/", "Overview", LayoutDashboard],
  ["/inventory", "Inventory", Package],
  ["/agents", "Agent control", Network],
  ["/forecast", "Demand forecasting", ChartNoAxesCombined],
  ["/allocation", "Inventory allocation", ArrowLeftRight],
  ["/warehouses", "Warehouses", Warehouse],
  ["/transfers", "Logistics & transfers", Truck],
  ["/analytics", "Analytics & reports", ChartPie],
  ["/simulation", "Simulation center", FlaskConical],
  ["/settings", "Settings", Settings],
] as const;
const descriptions: Record<string, string> = {
  "/": "A clear view of your inventory. A smarter way to move it.",
  "/inventory": "Every product, every location, one source of truth.",
  "/agents": "Ten specialized agents. One coordinated retail network.",
  "/forecast": "Turn historical demand into confident replenishment decisions.",
  "/allocation":
    "Balance online and offline demand with constrained optimization.",
  "/warehouses": "Monitor network capacity, replenishment and distribution.",
  "/transfers": "Follow inventory movements across your retail network.",
  "/analytics": "Understand performance with evidence from your operations.",
  "/simulation": "Explore demand and supply shocks in an isolated sandbox.",
  "/settings": "Configure your team, models and operating constraints.",
};

function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [email, setEmail] = useState("admin@retail.local");
  const [password, setPassword] = useState("");
  const mutation = useMutation({
    mutationFn: async () => {
      const r = await api.post("/api/auth/login", { email, password });
      sessionStorage.setItem("token", r.data.access_token);
      onLogin(r.data.user);
    },
  });
  return (
    <div className="login-screen">
      <div className="login-story">
        <div className="brand">
          <div className="brand-mark">
            <Network />
          </div>
          NEXUS<span>RETAIL</span>
        </div>
        <span className="eyebrow">INVENTORY INTELLIGENCE</span>
        <h1>
          The right stock.
          <br />
          The right place.
          <br />
          <em>Working together.</em>
        </h1>
        <p>
          Connect stores, fulfillment centers and warehouses with coordinated,
          auditable agent decisions.
        </p>
        <div className="login-network">
          WAREHOUSES <span>↗</span> AGENTS <span>↗</span> CHANNELS
        </div>
      </div>
      <form
        className="login-form"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <Badge value="synthetic demonstration" />
        <h2>Welcome to your network</h2>
        <p>Sign in to the inventory intelligence workspace.</p>
        <label>
          Email address
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        {mutation.error && <ErrorBox message={errorText(mutation.error)} />}
        <button className="primary" disabled={mutation.isPending}>
          {mutation.isPending ? "Signing in…" : "Sign in to workspace"}{" "}
          <ArrowUpRight size={17} />
        </button>
        <small>
          Local demo password: <code>RetailDemo!2026</code>
          <br />
          Use SEED_PASSWORD if you configured your own.
        </small>
      </form>
    </div>
  );
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [toast, setToast] = useState("");
  useEffect(() => {
    if (sessionStorage.getItem("token"))
      api
        .get("/api/auth/me")
        .then((r) => setUser(r.data))
        .catch((e) => setToast(errorText(e)))
        .finally(() => setChecking(false));
    else setChecking(false);
    const expire = () => setUser(null);
    const apiError = (e: Event) => setToast((e as CustomEvent<string>).detail);
    window.addEventListener("session-expired", expire);
    window.addEventListener("api-error", apiError);
    return () => {
      window.removeEventListener("session-expired", expire);
      window.removeEventListener("api-error", apiError);
    };
  }, []);
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(""), 5000);
      return () => clearTimeout(t);
    }
  }, [toast]);
  if (checking) return <Loading />;
  return (
    <Toast.Provider value={setToast}>
      {user ? (
        <Auth.Provider
          value={{
            user,
            canManage: ["Administrator", "Inventory Manager"].includes(
              user.role,
            ),
            canOperate: [
              "Administrator",
              "Inventory Manager",
              "Warehouse Manager",
            ].includes(user.role),
          }}
        >
          <Shell
            logout={() => {
              sessionStorage.removeItem("token");
              client.clear();
              setUser(null);
            }}
          />
        </Auth.Provider>
      ) : (
        <Login onLogin={setUser} />
      )}{" "}
      {toast && (
        <div className="toast" role="status">
          <Check size={17} />
          {toast}
        </div>
      )}
    </Toast.Provider>
  );
}

function Shell({ logout }: { logout: () => void }) {
  const [collapsed, setCollapsed] = useState(false);
  const [notifications, setNotifications] = useState(false);
  const [connected, setConnected] = useState(false);
  const { user } = useContext(Auth);
  const qc = useQueryClient();
  const path = useLocation().pathname;
  const title = nav.find((n) => n[0] === path)?.[1] || "Overview";
  const notices = useData<Notification[]>("/api/notifications");
  const read = useAction<number>(
    (id) => api.put(`/api/notifications/${id}/read`),
    "Notification marked read",
  );
  useEffect(() => {
    if(import.meta.env.VITE_REALTIME_MODE==='polling')return;
    const ws = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`,
    );
    ws.onopen = () =>
      ws.send(JSON.stringify({ token: sessionStorage.getItem("token") }));
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      setConnected(true);
      if (m.type !== "connected") qc.invalidateQueries();
    };
    ws.onerror = () => setConnected(false);
    ws.onclose = () => setConnected(false);
    return () => ws.close();
  }, [qc]);
  return (
    <div className={`app ${collapsed ? "collapsed" : ""}`}>
      <aside className="sidebar">
        <Link to="/" className="brand">
          <div className="brand-mark">
            <Network size={22} />
          </div>
          <div>
            NEXUS<span>RETAIL</span>
          </div>
        </Link>
        <div className="workspace">
          <span className="workspace-symbol">N</span>
          <div>
            Retail operations<small>Demo workspace</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map(([url, name, Icon], i) => (
            <React.Fragment key={url}>
              {i === 8 && (
                <div className="nav-label second-label">MANAGEMENT</div>
              )}
              <NavLink to={url} end={url === "/"}>
                <Icon size={19} />
                <span>{name}</span>
                {url === "/agents" && <b>10</b>}
              </NavLink>
            </React.Fragment>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="network-status">
            <span className="live-dot" />
            <span>Network operational</span>
          </div>
          <p>Coordinated. Connected. In control.</p>
          <button onClick={logout}>
            <LogOut size={16} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button"
              aria-label="Toggle sidebar"
              onClick={() => setCollapsed(!collapsed)}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{title}</strong>
          </div>
          <div className="top-actions">
            <span className="connection">
              <i className={connected ? "live-dot" : "poll-dot"} />
              {connected ? "Live updates" : "Polling · 15s"}
            </span>
            <button
              className="icon-button bell"
              aria-label="Notifications"
              onClick={() => setNotifications(!notifications)}
            >
              <Bell size={20} />
              {notices.data?.some((n) => !n.read) && <i />}
            </button>
            <div className="user-avatar">
              {user.name
                .split(" ")
                .map((s) => s[0])
                .slice(0, 2)
                .join("")}
            </div>
            <div className="user-info">
              <strong>{user.name}</strong>
              <small>{user.role}</small>
            </div>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">NEXUS / {title.toUpperCase()}</div>
              <h1>{path === "/" ? "Network overview" : title}</h1>
              <p>{descriptions[path]}</p>
            </div>
            <span className="demo-tag">
              <span className="live-dot" />
              Synthetic data environment
            </span>
          </div>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/forecast" element={<Forecasting />} />
            <Route path="/allocation" element={<Allocation />} />
            <Route path="/warehouses" element={<Warehouses />} />
            <Route path="/transfers" element={<Transfers />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/simulation" element={<Simulation />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route
              path="*"
              element={
                <Empty text="Page not found. Choose a workspace page from the sidebar." />
              }
            />
          </Routes>
          <footer>
            NEXUS RETAIL <span>Autonomous inventory coordination</span>
            <span>Local deterministic agents · No paid AI services</span>
          </footer>
        </main>
      </div>
      {notifications && (
        <Drawer title="Notifications" onClose={() => setNotifications(false)}>
          {notices.data?.map((n) => (
            <div className="notification" key={n.id}>
              <Badge value={n.severity} />
              <p>{n.title}</p>
              <small>{new Date(n.created_at).toLocaleString()}</small>
              {!n.read && (
                <button onClick={() => read.mutate(n.id)}>Mark read</button>
              )}
            </div>
          ))}
        </Drawer>
      )}
    </div>
  );
}

export {
  Agents,
  Allocation,
  App,
  Auth,
  Dashboard,
  Forecasting,
  Inventory,
  Simulation,
  Toast,
};
const root = document.getElementById("root");
if (root)
  createRoot(root).render(
    <React.StrictMode>
      <QueryClientProvider client={client}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </React.StrictMode>,
  );
