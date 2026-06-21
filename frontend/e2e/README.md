# 프론트 E2E (Playwright)

07 §5. 핵심 사용자 여정을 자동 회귀로 보호합니다.

## 실행

```bash
npm run e2e            # 헤드리스 전체
npm run e2e:ui         # UI 모드(디버깅)
npx playwright test landing.spec.ts --project=desktop   # 스모크만
```

`playwright.config.ts` 의 `webServer` 가 `:3000` dev 서버를 재사용합니다(없으면 기동).

## 두 모드 (07 §5.2)

- **dev 모드(기본·CI)**: 백엔드를 `DEV_AUTH=true` + `SUPABASE_*`/`GOOGLE_API_KEY` 비움으로 :8000 에 띄우고,
  프론트는 Supabase 미설정(`.env`)으로 빌드해 DevLogin 을 노출합니다. mock AI 라 결정적이어서 안정적으로 어서션할 수 있습니다.
  `auth.spec.ts`(E1~) 등 인증·데이터 시나리오는 이 모드에서만 통과합니다(실키 모드면 자동 skip).
- **실키 모드(@realkey)**: Google OAuth·실 Gemini 가 필요해 CI 기본에서 제외하고 수동/야간으로 돌립니다. 테스트 제목에 `@realkey` 태그를 붙이고, CI 는 `npm run e2e:ci`(= `--grep-invert @realkey`)로 제외합니다.

> `landing.spec.ts` 는 백엔드 무관 스모크 + 반응형(360/768/1280) 가로 오버플로 점검이라 어느 모드에서도 통과합니다.

## 시나리오 (07 §5.4)

- `landing.spec.ts`: 랜딩→로그인 진입, 반응형 스모크(E17).
- `auth.spec.ts`: dev 로그인(E1 교사, E2 학생) — dev 모드 전용.
- (후속) E4 발제·E5 책생성·E6 기획·E7 집필 SSE·E8 유도게이트·E9 수정요청·E11 단어·E12 학습·E14 대시보드·E15 콘솔·E16 역할가드, 그리고 02~06 신규 기능 시나리오(§5.5).

## CI (07 §5.7, 후속)

PR 에서 `npm run build` + `lint` + `npm run e2e:ci`(dev, @realkey 제외)를 돌립니다. 실패 시 trace/screenshot 아티팩트를 업로드합니다. 백엔드 dev 모드 webServer 는 백엔드 세션과 합의해 추가합니다.
