import { defineConfig, devices } from "@playwright/test";

// The end-to-end tests run against the real stack: the FastAPI backend serving the built UI
// (run `npm run build` first). No AI provider is contacted; everything uses Demo mode.
const python = process.env.E2E_PYTHON ?? "python";
const port = 8123;

export default defineConfig({
  testDir: "e2e",
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: { baseURL: `http://127.0.0.1:${port}`, trace: "retain-on-failure" },
  webServer: {
    command: `"${python}" -m uvicorn code_review.api:app_factory --factory --port ${port}`,
    cwd: "../backend",
    url: `http://127.0.0.1:${port}/api/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    env: { FRONTEND_DIST: "../frontend/dist", LLM_API_KEY: "", OPENROUTER_API_KEY: "" },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
