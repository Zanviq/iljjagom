# 프론트 E2E (Playwright)

07 §5. 핵심 사용자 여정을 자동 회귀로 보호한다.

## 실행

```bash
npm run e2e            # 헤드리스 전체
npm run e2e:ui         # UI 모드(디버깅)
npx playwright test landing.spec.ts --project=desktop   # 스모크만
```

`playwright.config.ts`의 `webServer`가 `:3000` dev 서버를 재사용(없으면 기동)한다.

## 두 모드 (07 §5.2)

- **dev 모드(기본·CI)**: 백엔드를 `DEV_AUTH=true` + `SUPABASE_*`/`GOOGLE_API_KEY` 비움으로 :8000에 띄우고,
  프론트는 Supabase 미설정(`.env`)으로 빌드 → DevLogin 노출. mock AI라 결정적이라 안정적 어서션 가능.
  `auth.spec.ts`(E1~) 등 인증·데이터 시나리오는 이 모드에서만 통과(실키 모드면 자동 skip).
- **실키 모드(@realkey)**: Google OAuth·실 Gemini 필요 → CI 기본 제외, 수동/야간. (현재 미태깅, 후속.)

> `landing.spec.ts`는 백엔드 무관 스모크 + 반응형(360/768/1280) 가로 오버플로 점검이라 어느 모드에서도 통과.

## 시나리오 (07 §5.4)

- `landing.spec.ts`: 랜딩→로그인 진입, 반응형 스모크(E17).
- `auth.spec.ts`: dev 로그인(E1 교사, E2 학생) — dev 모드 전용.
- (후속) E4 발제·E5 책생성·E6 기획·E7 집필 SSE·E8 유도게이트·E9 수정요청·E11 단어·E12 학습·E14 대시보드·E15 콘솔·E16 역할가드, 그리고 02~06 신규 기능 시나리오(§5.5).

## CI (07 §5.7, 후속)

PR에서 `npm run build`+`lint`+`e2e`(dev). 실패 시 trace/screenshot 아티팩트 업로드. 백엔드 dev 모드 webServer는 백엔드 세션과 합의해 추가.
