# Pulse24 Demo Panel

`mkt24.net`의 정보 구조와 모바일 우선 흐름을 참고해 제작한 데모용 SMM 패널입니다.  
브랜드명, 문구, 배너 자산은 그대로 복제하지 않고, `홈 → 상품목록 → 상품상세 → 충전 → 주문내역 → 마이` UX와 플랫폼/카테고리/상품/주문 DB 구조를 별도 구현했습니다.

## 실행

```bash
export SMM_PANEL_ADMIN_PASSWORD="강한관리자비밀번호"
python3 smm_panel/server.py --host 127.0.0.1 --port 8024
```

브라우저에서 `http://127.0.0.1:8024` 로 접속하면 됩니다.

분리 배포를 준비할 때는 `smm_panel/.env.example` 의 항목을 기준으로 환경변수를 맞추는 것을 권장합니다.

## 보안 기본값

- `/admin` 및 `/api/admin/*` 는 관리자 로그인 세션이 있어야만 접근할 수 있습니다.
- 공급사 API 키는 관리자 화면으로 평문이 다시 내려오지 않고, 마스킹된 상태만 표시됩니다.
- 고객 목록, 주문 목록, 사용자 패널에서는 이메일/전화번호가 마스킹된 값만 노출됩니다.
- 관리자 상세 화면에서만 고객 원본 정보가 조회되며, 응답은 `Cache-Control: no-store` 로 전송됩니다.
- 관리자 세션 쿠키는 `HttpOnly`, `SameSite=Strict` 로 발급되고, HTTPS 프록시 뒤에서는 `Secure` 가 자동 적용됩니다.
- 관리자 로그인은 연속 실패 횟수를 제한해 무차별 대입 시도를 완화합니다.
- 허용된 Origin 에 대해서만 CORS 를 열고, 관리자 POST 요청에는 CSRF 토큰 검증을 수행합니다.
- `link-preview` 는 내부망, localhost, 사설 IP 대역으로 연결되지 않도록 차단합니다.
- 주문, 충전, 링크 미리보기, 방문 수집 API 는 IP 단위 속도 제한이 적용됩니다.

## 구성

- 백엔드: Python 표준 라이브러리 HTTP 서버 + SQLite
- 프론트엔드: 정적 HTML/CSS/Vanilla JS SPA
- 저장소: `smm_panel/data/smm_panel.db`

## 분리 배포 설계

추후 `Vercel 프론트 + 별도 API + Supabase` 구조로 옮길 수 있도록 현재 코드도 그 방향을 기준으로 정리되어 있습니다.

- 프론트엔드:
  - `smm-api-base-url` 메타값을 읽어 API 서버를 분리해서 호출할 수 있습니다.
  - 관리자 API 호출은 `credentials: include` 와 CSRF 헤더를 함께 사용합니다.
  - 공급사 API 키나 서비스 롤 키는 프론트로 절대 내려주지 않습니다.
- 백엔드:
  - `SMM_PANEL_ALLOWED_ORIGINS` 로 허용 Origin 을 제한하고, 관리자 세션 쿠키 정책을 환경변수로 제어할 수 있습니다.
  - 공급사 호출, 링크 검증, 주문 생성, 관리자 작업은 모두 백엔드에서만 처리해야 합니다.
  - 추후 Supabase 로 이관할 때도 `service_role` 키는 백엔드에만 두고, 프론트에는 공개 키만 사용해야 합니다.
- 데이터베이스:
  - 현재는 SQLite 이지만, 다음 단계에서는 `PanelStore` 를 저장소 인터페이스 기준으로 분리해 `SQLiteAdapter -> Supabase/PostgresAdapter` 로 교체하는 구조를 권장합니다.
  - 사용자 인증을 Supabase Auth 로 옮길 경우에도, 공급사 비밀값과 관리자 권한 작업은 별도 백엔드에서 계속 수행하는 편이 안전합니다.

## Vercel 프런트 배포

이 저장소는 Vercel에서 정적 SPA 프런트로 배포할 수 있도록 `vercel.json` 과 `build-static.mjs` 를 포함합니다.

- 빌드 시 `static/index.html` 을 `dist/index.html` 로 복사합니다.
- `SMM_PANEL_PUBLIC_API_BASE_URL` 값이 있으면 빌드 단계에서 프런트 HTML 메타 태그에 주입합니다.
- 모든 일반 경로는 `index.html` 로 재작성되고, `/api/*` 는 프런트 프로젝트에서 직접 처리하지 않도록 `404` 로 막습니다.

Vercel 프로젝트에는 최소한 아래 환경변수를 설정하는 것을 권장합니다.

- `SMM_PANEL_PUBLIC_API_BASE_URL`: 실제 백엔드 API 주소 예) `https://api.example.com`

이 값이 비어 있으면 프런트는 같은 Origin의 `/api/*` 를 호출하게 되므로, 프런트와 백엔드를 분리 배포할 때는 반드시 설정해 두는 편이 안전합니다.

## 권장 환경변수

- `SMM_PANEL_PUBLIC_API_BASE_URL`: 프론트가 호출할 API 기본 주소
- `SMM_PANEL_ALLOWED_ORIGINS`: CORS 허용 Origin 목록
- `SMM_PANEL_PUBLIC_APP_ORIGIN`: 대표 프론트 Origin
- `SMM_PANEL_COOKIE_DOMAIN`: 관리자 세션 쿠키 공유 도메인
- `SMM_PANEL_ADMIN_COOKIE_SAMESITE`: `Strict`, `Lax`, `None`
- `SMM_PANEL_FORCE_SECURE_COOKIES`: HTTPS 강제 시 `true`

운영에서는 `app.example.com` 과 `api.example.com` 처럼 같은 상위 도메인 아래에서 프론트와 API 를 나누는 구성을 추천합니다. 이렇게 하면 관리자 세션 쿠키를 상대적으로 안정적으로 유지할 수 있습니다.

## 주요 화면

- 홈: 블루 히어로, 플랫폼 탭, 배너 캐러셀, 추천 서비스, 지원 바로가기
- 주문: 좌측 플랫폼 레일 + 우측 상품 카드형 목록
- 상세: 옵션 칩, 동적 주문 폼, 주의/환불 안내, HTML 상세 설명
- 충전: 캐시 카드와 거래 내역
- 내역: 주문 상태별 필터와 카드형 주문 이력
- 마이: FAQ, 공지, 가이드, 지원 링크

## DB 구조

핵심 테이블은 아래와 같습니다.

- `users`: 데모 사용자, 잔액, 등급
- `platform_sections`: 인스타그램/유튜브/웹툰 등 플랫폼 탭
- `platform_groups`: 플랫폼 내부 그룹
- `product_categories`: 상품 상세 페이지 단위
- `products`: 실제 주문 옵션 단위, 가격/수량 제한/폼 구조 JSON 포함
- `home_banners`, `home_interest_tags`, `home_spotlights`: 홈 화면 콘텐츠
- `support_links`, `benefits`, `notices`, `faqs`: 지원/안내 콘텐츠
- `orders`, `order_fields`: 주문 헤더와 입력 필드 스냅샷
- `balance_transactions`: 충전/주문 차감 내역

`products.form_structure_json` 에 주문 폼 스키마를 JSON으로 저장해서, 상품마다 계정형/URL형/키워드형 폼을 다르게 렌더링합니다.
