import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 180000,
  expect: { timeout: 15000 },
  use: {
    baseURL: "http://localhost:1420",
    headless: true,
    viewport: { width: 1400, height: 900 },
  },
});
