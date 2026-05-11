# Architecture Guidelines

이 문서는 고객용 UI, 관리자 UI, API, DB 기능이 한 파일에 다시 누적되지 않도록 유지하기 위한 작업 규칙입니다.

## 핵심 원칙

- `static/app.js` 는 bootstrap, route orchestration, public/admin 이벤트 모듈 등록만 담당한다.
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
| App entry | `static/app.js` | 초기화, route 분기, 공통 API 호출, public/admin 이벤트 모듈 등록 |
| Public pages | `static/public/pages.js` | 홈, 상품, 상세, 주문내역, 마이 렌더 |
| Public auth | `static/public/auth.js`, `static/public/auth-state.js` | 로그인/회원가입 UI와 검증 상태 |
| Public charge | `static/public/charge.js` | 충전 UI, 충전내역 UI |
| Public events | `static/public/events.js` | 고객용 click/input/change/submit/keydown 이벤트 위임 |
| Admin shell | `static/admin/pages.js` | 관리자 프레임, 네비게이션, 섹션 라우팅 |
| Admin sections | `static/admin/sections.js` | 관리자 각 섹션 렌더, 미리보기, 통계 렌더 |
| Admin events | `static/admin/events.js` | 관리자용 click/input/change/submit/mouse 이벤트 위임 |
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

`core.py` 의 `PanelStore` 는 아직 서버 호환성을 위한 facade 로 유지한다. 신규/수정 기능은 먼저 아래 도메인 모듈에 배치하고, `PanelStore` 는 필요한 모듈을 조합하거나 얇게 위임한다.

| 도메인 | 권장 위치 |
|---|---|
| DB 연결/마이그레이션 | `backend/db.py` |
| 고객 인증/동의 | `backend/auth.py`, `backend/consents.py` |
| Wallet/충전/결제 | `backend/wallet.py`, `backend/payments.py` |
| 주문 | `backend/orders.py` |
| 상품/카탈로그 | `backend/catalog.py` |
| 공급사 | `backend/integrations/suppliers.py` |
| Cafe24 | `backend/integrations/cafe24.py` |
| 관리자 | `backend/admin.py` |
| 분석 | `backend/analytics.py` |

### 백엔드 작업 규칙

1. `core.py` 에 새 외부 API 클라이언트, 순수 유틸, 해시/검증 로직을 추가하지 않는다.
2. DB 부트/마이그레이션 변경은 `backend/db.py` 의 `PanelStoreDatabaseMixin` 에 추가한다.
3. 고객 인증, 이메일 인증, 비밀번호 정책 변경은 `backend/auth.py` 에 먼저 추가한다.
4. 주문 중복 방지, idempotency, 주문 payload 유틸은 `backend/orders.py` 에 둔다.
5. 지갑 원장/충전 코드/결제 웹훅 검증은 `backend/wallet.py` 또는 `backend/payments.py` 에 둔다.
6. 공급사/Cafe24 HTTP 호출은 `backend/integrations/` 하위 모듈에 둔다.
7. `core.py` 에 남는 코드는 기존 `server.py` 호환 facade, DB 트랜잭션 오케스트레이션, 단계적 이전 중인 레거시 메서드로 제한한다.
8. 새 모듈은 타입 힌트를 유지하고, `core.py` 양방향 import 를 만들지 않는다.

## 자동 구조 검사

`build-static.mjs` 는 빌드 전에 `scripts/architecture-check.mjs` 를 실행한다. 따라서 Vercel 배포나 로컬 정적 빌드에서 아래 위반이 있으면 실패한다.

- 파일별 라인 예산 초과
- public 모듈에서 admin 모듈 import
- admin 모듈에서 public 모듈 import
- `static/app.js` 에 admin render section 함수 재누적
- public index 에 admin stylesheet 직접 로드

라인 예산은 리팩터링 진행 상황에 맞춰 점진적으로 낮춘다. 예산을 올리는 것은 예외 상황이며, 먼저 새 모듈 분리를 검토한다.

## 현재 남은 구조 부채

- `static/app.js` 는 8천 줄에서 약 3천 줄대로 줄었고, 이벤트 핸들러는 public/admin 모듈로 분리되었다. 아직 route orchestration 과 공통 API context 가 크다.
- `static/styles/shared.css` 는 아직 5천 줄 규모이고 public/admin 스타일이 일부 섞여 있다.
- `core.py` 는 아직 1만 줄 이상이며 `PanelStore` 의 DB 접근 메서드가 많이 남아 있다.
- 백엔드는 DB 부트/마이그레이션, 인증 유틸, 주문 idempotency, 지갑/결제 유틸, Cafe24/Supplier 클라이언트가 1차 분리되었다.
- 다음 리팩터링 우선순위는 `PanelStore` 의 주문/지갑/관리자 DB 메서드를 도메인 repository 또는 mixin 으로 추가 분리하고, `static/app.js` 의 event handler/API client 와 `shared.css` 를 정리하는 것이다.
