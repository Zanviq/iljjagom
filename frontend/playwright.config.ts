import { defineConfig, devices } from "@playwright/test";

/**
 * 프론트 E2E (07 §5). 두 모드:
 * - dev 모드(기본·CI): 백엔드 DEV_AUTH=true + SUPABASE/GOOGLE_API_KEY 비움 → 인메모리·mock AI(결정적),
 *   프론트는 .env(Supabase 미설정)로 DevLogin 노출. auth 의존 시나리오는 이 모드에서만 동작.
 * - 실키 모드(@realkey): Google OAuth·실 Gemini 필요 → CI 기본 제외(수동/야간).
 *
 * 백엔드는 별도 세션이 띄운다(이 webServer는 프론트만 관리). 백엔드가 dev 모드로 :8000에 떠 있어야
 * auth 시나리오가 통과한다. 백엔드 미가동이어도 landing 스모크는 통과.
 */
const PORT = Number(process.env.E2E_PORT ?? 3000);
const BASE_URL = process.env.E2E_BASE_URL ?? `http://localhost:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    { name: "tablet", use: { ...devices["Desktop Chrome"], viewport: { width: 768, height: 1024 } } },
    { name: "mobile", use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 } } },
  ],
  // 이미 떠 있는 dev 서버(:3000)를 재사용. 없으면 새로 띄운다.
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
