import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Mounted at twinval.com/entry — both asset paths and the SPA fallback
// must resolve under /entry/.
export default defineConfig({
  base: "/entry/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
