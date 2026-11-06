import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
const target = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": target,
      "/health": target,
      "/ws": { target: target.replace("http", "ws"), ws: true },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          charts: ["recharts"],
          framework: ["react", "react-dom", "react-router-dom"],
          query: ["@tanstack/react-query", "axios"],
        },
      },
    },
  },
});
