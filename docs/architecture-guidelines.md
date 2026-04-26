# Architecture Guidelines

이 문서는 고객용 UI, 관리자 UI, API, DB 기능이 한 파일에 다시 누적되지 않도록 유지하기 위한 작업 규칙입니다.

## 핵심 원칙

- `static/app.js` 는 bootstrap, route orchestration, global event delegation 만 담당한다.
- 고객용 화면/상태/상호작용은 `static/public/` 아래에 둔다.
- 관리자 화면/상태/상호작용은 `static/admin/` 아래에 둔다.
- 양쪽에서 같이 쓰는 순수 유틸만 `static/shared/` 아래에 둔다.
- public 모듈은 admin 모듈을 import 하지 않는다.
- admin 모듈은 public 모듈을 import 하지 않는다.
- 신규 CSS는 먼저 `static/styles/public.css` 또는 `static/styles/admin.css` 에 둔다.
- `static/styles/shared.css` 는 색상 토큰, reset, 진짜 공용 컴포넌트만 둔다.
- 백엔드 신규 기능은 `core.py` 에 바로 누적하지 말고, 다음 분리 대상 도메인에 맞춰 추가한다.

## 프론트 파일 책임

| 영역 | 위치 | 책임 |
|---|---|---|
| App entry | `static/app.js` | 초기화, route 분기, 공통 API 호출, 전역 이벤트 연결 |
| Public pages | `static/public/pages.js` | 홈, 상품, 상세, 주문내역, 마이 렌더 |
| Public auth | `static/public/auth.js`, `static/public/auth-state.js` | 로그인/회원가입 UI와 검증 상태 |
| Public charge | `static/public/charge.js` | 충전 UI, 충전내역 UI |
| Admin shell | `static/admin/pages.js` | 관리자 프레임, 네비게이션, 섹션 라우팅 |
| Admin sections | `static/admin/sections.js` | 관리자 각 섹션 렌더, 미리보기, 통계 렌더 |
| Shared route/runtime | `static/shared/` | 라우트 파싱, runtime config, 순수 유틸 |

## 새 기능 추가 규칙

1. 고객 화면 변경이면 `static/public/` 부터 찾는다.
2. 관리자 화면 변경이면 `static/admin/` 부터 찾는다.
3. API 호출 함수가 커지면 `static/public/api.js`, `static/admin/api.js`, `static/shared/api-client.js` 로 분리한다.
4. 전역 click/input/submit handler 에 직접 기능을 계속 추가하지 않는다.
5. 이벤트가 30줄 이상이면 public/admin 전용 handler 함수로 뺀다.
6. 새 렌더 함수가 admin 전용이면 `static/admin/sections.js` 또는 새 `static/admin/*.js` 파일로 둔다.
7. 새 렌더 함수가 public 전용이면 `static/public/*.js` 로 둔다.
8. shared 로 올리는 함수는 DOM, state, route, admin/public을 직접 참조하지 않는 순수 함수만 허용한다.

## 백엔드 분리 방향

현재 `core.py` 는 아직 모놀리식이다. 다음 기능 수정부터는 아래 도메인으로 분리한다.

| 도메인 | 권장 위치 |
|---|---|
| DB 연결/마이그레이션 | `backend/db.py`, `backend/migrations.py` |
| 고객 인증/동의 | `backend/auth.py`, `backend/consents.py` |
| Wallet/충전/결제 | `backend/wallet.py`, `backend/payments.py` |
| 주문 | `backend/orders.py` |
| 상품/카탈로그 | `backend/catalog.py` |
| 공급사 | `backend/suppliers.py` |
| 관리자 | `backend/admin.py` |
| 분석 | `backend/analytics.py` |

## 자동 구조 검사

`build-static.mjs` 는 빌드 전에 `scripts/architecture-check.mjs` 를 실행한다. 따라서 Vercel 배포나 로컬 정적 빌드에서 아래 위반이 있으면 실패한다.

- 파일별 라인 예산 초과
- public 모듈에서 admin 모듈 import
- admin 모듈에서 public 모듈 import
- `static/app.js` 에 admin render section 함수 재누적
- public index 에 admin stylesheet 직접 로드

라인 예산은 리팩터링 진행 상황에 맞춰 점진적으로 낮춘다. 예산을 올리는 것은 예외 상황이며, 먼저 새 모듈 분리를 검토한다.

## 현재 남은 구조 부채

- `static/app.js` 는 8천 줄에서 약 5천 줄로 줄었지만, 아직 이벤트 핸들러와 API orchestration 이 크다.
- `static/styles/shared.css` 는 아직 5천 줄 규모이고 public/admin 스타일이 일부 섞여 있다.
- `core.py` 는 아직 1만 줄 이상이며 백엔드 도메인 분리가 필요하다.
- 다음 리팩터링 우선순위는 `static/app.js` 의 event handler 분리, API client 분리, `shared.css` 정리, `core.py` 도메인 분리다.
