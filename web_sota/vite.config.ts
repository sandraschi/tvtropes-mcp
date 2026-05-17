import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 10965,
    host: "127.0.0.1",
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:10964",
        changeOrigin: true,
      },
      "/mcp": {
        target: "http://127.0.0.1:10964",
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 10965,
    host: "127.0.0.1",
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:10964",
        changeOrigin: true,
      },
      "/mcp": {
        target: "http://127.0.0.1:10964",
        changeOrigin: true,
      },
    },
  },
});
