import { useQuery } from "@tanstack/react-query";
import axios from "axios";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  timeout: 120000,
});
api.interceptors.request.use((c) => {
  const token = sessionStorage.getItem("token");
  if (token) c.headers.Authorization = `Bearer ${token}`;
  return c;
});
api.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e.response?.status === 401) {
      sessionStorage.removeItem("token");
      window.dispatchEvent(new Event("session-expired"));
    }
    window.dispatchEvent(
      new CustomEvent("api-error", { detail: errorText(e) }),
    );
    return Promise.reject(e);
  },
);
export function useData<T>(path: string, enabled = true) {
  return useQuery<T>({
    queryKey: [path],
    queryFn: async () => (await api.get(path)).data,
    enabled,
    refetchInterval: 15000,
  });
}
export function errorText(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data?.detail;
    return typeof d === "string"
      ? d
      : Array.isArray(d)
        ? d.map((x: { msg: string }) => x.msg).join("; ")
        : e.message;
  }
  return e instanceof Error ? e.message : "Operation failed";
}
export const number = (n: number | null | undefined) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(n);
export const money = (n: number | null | undefined) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      }).format(n);
export function csvDownload(rows: Record<string, unknown>[], name: string) {
  if (!rows.length) return;
  const keys = Object.keys(rows[0]);
  const quote = (v: unknown) =>
    '"' +
    String(typeof v === "object" ? JSON.stringify(v) : (v ?? ""))
      .replace(/^[=+@-]/, "'$&")
      .replaceAll('"', '""') +
    '"';
  const csv = [
    keys.map(quote).join(","),
    ...rows.map((r) => keys.map((k) => quote(r[k])).join(",")),
  ].join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}
