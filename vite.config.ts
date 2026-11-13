import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  root: "ui",
  server: { port: 1420, strictPort: true },
  build: { outDir: "dist", emptyOutDir: true },
  test: {
    environment: "jsdom",
    root: ".",
    include: ["ui/src/**/*.test.ts", "ui/src/**/*.test.tsx"],
  },
});
