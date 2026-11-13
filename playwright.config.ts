import os from "node:os";
import path from "node:path";
import { defineConfig } from "@playwright/test";

// Eigener Programmordner für die Tests, damit Einstellungen, Vorlagen und Exporte des Benutzers unberührt bleiben.
const TEST_HOME = path.join(os.tmpdir(), "cadstudio-e2e-home");

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 180000,
  expect: { timeout: 15000 },
  // Ein Dienst mit gemeinsamem Zustand (Vorlagen, zuletzt geöffnete Projekte): Tests nacheinander
  workers: 1,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://localhost:1420",
    headless: true,
    viewport: { width: 1400, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "python -m sidecar.server",
      url: "http://127.0.0.1:47321/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
      env: { ...(process.env as Record<string, string>), CADSTUDIO_HOME: TEST_HOME, PYTHONUTF8: "1" },
    },
    {
      command: "npm run dev",
      url: "http://localhost:1420",
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
  ],
});
