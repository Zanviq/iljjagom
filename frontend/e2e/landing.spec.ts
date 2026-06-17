import { expect, test } from "@playwright/test";

/**
 * 백엔드 무관 스모크: 랜딩·로그인 진입(dev/실키 모드 양쪽에서 통과).
 * 인증·데이터 의존 시나리오는 auth.spec.ts(dev 모드 전용).
 */
test("랜딩이 렌더되고 로그인으로 이동한다", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "일짜곰" })).toBeVisible();

  const start = page.getByRole("link", { name: "시작하기" });
  await expect(start).toBeVisible();
  await start.click();

  await expect(page).toHaveURL(/\/login$/);
  // 로그인 컨트롤은 모드에 따라 다르다: dev=이메일 입력, 실키=Google 버튼.
  const devEmail = page.getByLabel("이메일");
  const googleBtn = page.getByRole("button", { name: /Google/ });
  await expect(devEmail.or(googleBtn).first()).toBeVisible();
});

test("E17 반응형 스모크: 랜딩·로그인이 360/768/1280에서 가로 오버플로 없음", async ({
  page,
}) => {
  for (const path of ["/", "/login"]) {
    for (const width of [360, 768, 1280]) {
      await page.setViewportSize({ width, height: 800 });
      await page.goto(path);
      // 문서 폭이 뷰포트를 넘지 않아야 한다(가로 스크롤 방지).
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(
        overflow,
        `${path} @ ${width}px 가로 오버플로`,
      ).toBeLessThanOrEqual(1);
    }
  }
});
