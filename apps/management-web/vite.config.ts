import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8787" } },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("/ol/")) return "maps";
            if (id.includes("cytoscape")) return "graphs";
            if (id.includes("codemirror") || id.includes("@lezer"))
              return "editor";
            if (
              id.includes("antd") ||
              id.includes("@ant-design") ||
              id.includes("@rc-component") ||
              id.includes("/rc-")
            )
              return "antd";
            return "vendor";
          }
        },
      },
    },
  },
});
