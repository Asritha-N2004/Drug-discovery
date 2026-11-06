import { AlertCircle, ArrowUpRight, LoaderCircle, X } from "lucide-react";
import { type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { number } from "./api";
export function Badge({ value }: { value: string }) {
  return (
    <span className={`badge ${value.replaceAll(" ", "_")}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}
export function Card({
  title,
  subtitle,
  children,
  action,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {title && (
        <div className="card-head">
          <div>
            <h3>{title}</h3>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
export function Metric({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string;
  detail?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="metric">
      <div className="metric-label">
        {label}
        <span>{icon || <ArrowUpRight size={17} />}</span>
      </div>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </div>
  );
}
export function Empty({
  text = "No records yet. Run the workflow to generate results.",
}: {
  text?: string;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">◇</div>
      <p>{text}</p>
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading">
      <LoaderCircle className="spin" /> Loading network data…
    </div>
  );
}
export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="error" role="alert">
      <AlertCircle size={18} />
      {message}
    </div>
  );
}
export function Drawer({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="overlay" onClick={onClose}>
      <aside
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="card-head">
          <h2>{title}</h2>
          <button
            className="icon-button"
            aria-label="Close details"
            onClick={onClose}
          >
            <X />
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}
export function TrendChart({
  data,
  keys = ["online", "offline"],
  x = "month",
  height = 280,
}: {
  data: Record<string, unknown>[];
  keys?: string[];
  x?: string;
  height?: number;
}) {
  const colors = ["#3676ee", "#19b6a1", "#b9c9e6"];
  return (
    <div style={{ height, minWidth: 0 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            {keys.map((k, i) => (
              <linearGradient
                id={"fill-" + k}
                key={k}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop
                  offset="0%"
                  stopColor={colors[i % 3]}
                  stopOpacity={0.18}
                />
                <stop offset="100%" stopColor={colors[i % 3]} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid
            strokeDasharray="3 5"
            vertical={false}
            stroke="#e9edf3"
          />
          <XAxis
            dataKey={x}
            tick={{ fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            minTickGap={30}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={55}
          />
          <Tooltip />
          <Legend iconType="circle" />
          {keys.map((k, i) => (
            <Area
              key={k}
              type="monotone"
              dataKey={k}
              stroke={colors[i % 3]}
              fill={`url(#fill-${k})`}
              strokeWidth={2.5}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
export function Bars({
  data,
  keys = ["value"],
  x = "name",
  height = 280,
}: {
  data: Record<string, unknown>[];
  keys?: string[];
  x?: string;
  height?: number;
}) {
  return (
    <div style={{ height, minWidth: 0 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 5" vertical={false} />
          <XAxis
            dataKey={x}
            tick={{ fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={55}
          />
          <Tooltip />
          <Legend />
          {keys.map((k, i) => (
            <Bar
              key={k}
              dataKey={k}
              fill={["#3676ee", "#19b6a1", "#b6c8ec"][i % 3]}
              radius={[5, 5, 0, 0]}
              maxBarSize={38}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
export function Table({
  headers,
  children,
}: {
  headers: string[];
  children: ReactNode;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
export function Progress({ value }: { value: number }) {
  return (
    <div className="progress-row">
      <div className="progress">
        <i style={{ width: `${Math.min(100, value)}%` }} />
      </div>
      <small>{number(value)}%</small>
    </div>
  );
}
