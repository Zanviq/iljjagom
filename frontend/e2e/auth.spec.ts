import { expect, type Page, test } from "@playwright/test";

/**
 * dev 모드 인증 시나리오(07 §5.4 E1~). 백엔드가 dev 모드(DEV_AUTH·인메모리·mock AI)로
 * :8000에 떠 있어야 한다. 실키 모드(Google 로그인만)면 자동 skip.
 * desktop 프로젝트에서만 의미 있으므로 tablet/mobile에서는 skip.
 */

/** 고유 테스트 이메일(인메모리 상태 충돌 방지). */
function uniqueEmail(prefix: string): string {
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}_${Date.now().toString(36)}${rand}@test.kr`;
}

/**
 * dev 모드 로그인(DevLogin: 이메일+역할 → dev 토큰).
 * 실키 모드(Google 버튼만)면 false 반환 → 호출부 skip.
 */
async function devLogin(
  page: Page,
  email: string,
  role: "student" | "teacher",
): Promise<boolean> {
  await page.goto("/login");
  const emailInput = page.getByLabel("이메일");
  if (!(await emailInput.isVisible().catch(() => false))) return false;
  await emailInput.fill(email);
  await page
    .getByRole("radio", { name: role === "student" ? /학생/ : /교사/ })
    .check();
  await page.getByRole("button", { name: "시작하기" }).click();
  await expect(page).not.toHaveURL(/\/login$/, { timeout: 15_000 });
  return true;
}

test.describe("dev 인증 흐름", () => {
  test("E1 교사 dev 로그인 → 로그인 페이지 이탈", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "auth는 desktop만");
    const ok = await devLogin(page, uniqueEmail("teacher"), "teacher");
    test.skip(!ok, "실키 모드: DevLogin 없음");
    await expect(page).not.toHaveURL(/\/login$/);
  });

  test("E2 학생 dev 로그인 → 온보딩/홈 도달", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop", "auth는 desktop만");
    const ok = await devLogin(page, uniqueEmail("kid"), "student");
    test.skip(!ok, "실키 모드: DevLogin 없음");
    await expect(page).toHaveURL(/\/(onboarding|home)/);
  });
});
