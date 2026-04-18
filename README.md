# Pulse24 Panel

`mkt24.net`의 정보 구조와 모바일 우선 흐름을 참고해 제작한 실제 판매 지향형 SMM 패널입니다.  
브랜드명, 문구, 배너 자산은 그대로 복제하지 않고, `홈 → 상품목록 → 상품상세 → 로그인/회원가입 → 충전 → 주문내역 → 마이` UX와 플랫폼/카테고리/상품/주문/회원/동의 이력 DB 구조를 별도 구현했습니다.

## 실행

```bash
export SMM_PANEL_ADMIN_PASSWORD="강한관리자비밀번호"
export SMM_PANEL_SESSION_SECRET="충분히긴랜덤문자열"
python3 smm_panel/server.py --host 127.0.0.1 --port 8024
```

브라우저에서 `http://127.0.0.1:8024` 로 접속하면 됩니다.

Supabase/Postgres 모드로 실행할 때만 아래 의존성을 먼저 설치하면 됩니다.

```bash
python3 -m pip install -r requirements.txt
```

분리 배포를 준비할 때는 `smm_panel/.env.example` 의 항목을 기준으로 환경변수를 맞추는 것을 권장합니다.

## 보안 기본값

- `/admin` 및 `/api/admin/*` 는 관리자 로그인 세션이 있어야만 접근할 수 있습니다.
- 공급사 API 키는 관리자 화면으로 평문이 다시 내려오지 않고, 마스킹된 상태만 표시됩니다.
- 고객 목록, 주문 목록, 사용자 패널에서는 이메일/전화번호가 마스킹된 값만 노출됩니다.
- 관리자 상세 화면에서만 고객 원본 정보가 조회되며, 응답은 `Cache-Control: no-store` 로 전송됩니다.
- 관리자 세션 쿠키는 `HttpOnly`, `SameSite=Strict` 로 발급되고, HTTPS 프록시 뒤에서는 `Secure` 가 자동 적용됩니다.
- 로그인 세션은 서버 메모리가 아니라 서명된 토큰 쿠키로 유지되므로, Vercel Functions 같은 서버리스 환경에서도 인스턴스 교체 때문에 로그인이 바로 풀리지 않습니다.
- 관리자 로그인은 연속 실패 횟수를 제한해 무차별 대입 시도를 완화합니다.
- 허용된 Origin 에 대해서만 CORS 를 열고, 관리자 POST 요청에는 CSRF 토큰 검증을 수행합니다.
- `link-preview` 는 내부망, localhost, 사설 IP 대역으로 연결되지 않도록 차단합니다.
- 주문, 충전, 링크 미리보기, 방문 수집 API 는 IP 단위 속도 제한이 적용됩니다.

## 구성

- 백엔드: Python 표준 라이브러리 HTTP 서버 + `PanelStore`
- 프론트엔드: 정적 HTML/CSS/Vanilla JS SPA
- 저장소: 기본은 SQLite, `SMM_PANEL_DATABASE_URL` 이 있으면 Supabase/Postgres

## 분리 배포 설계

추후 `Vercel 프론트 + 별도 API + Supabase` 구조로 옮길 수 있도록 현재 코드도 그 방향을 기준으로 정리되어 있습니다.

- 프론트엔드:
  - `smm-api-base-url` 메타값을 읽어 API 서버를 분리해서 호출할 수 있습니다.
  - 관리자 API 호출은 `credentials: include` 와 CSRF 헤더를 함께 사용합니다.
  - 공급사 API 키나 서비스 롤 키는 프론트로 절대 내려주지 않습니다.
- 백엔드:
  - `SMM_PANEL_ALLOWED_ORIGINS` 로 허용 Origin 을 제한하고, 관리자 세션 쿠키 정책을 환경변수로 제어할 수 있습니다.
  - 공급사 호출, 링크 검증, 주문 생성, 관리자 작업은 모두 백엔드에서만 처리해야 합니다.
  - 현재 구조는 같은 Vercel 프로젝트 안에서 `/api/*` Python 함수로도 동작할 수 있도록 정리되어 있습니다.
  - 추후 Supabase 로 이관할 때도 `service_role` 키는 백엔드에만 두고, 프론트에는 공개 키만 사용해야 합니다.
- 데이터베이스:
  - `PanelStore` 는 기본 SQLite 로 동작하고, `SMM_PANEL_DATABASE_URL` 이 설정되면 Supabase/Postgres 로 연결됩니다.
  - Supabase 는 REST 키보다 Postgres 연결 문자열로 붙는 구성을 우선 권장합니다.
  - 사용자 인증을 Supabase Auth 로 옮길 경우에도, 공급사 비밀값과 관리자 권한 작업은 별도 백엔드에서 계속 수행하는 편이 안전합니다.

## Supabase 연결

현재 백엔드는 환경변수만 바꾸면 SQLite 대신 Supabase Postgres 를 사용할 수 있도록 준비되어 있습니다.

1. Supabase 프로젝트에서 Postgres 연결 문자열을 확인합니다.
2. 백엔드 환경변수에 아래 값을 넣습니다.

```bash
export SMM_PANEL_DATABASE_URL="postgresql://postgres.your-project:[PASSWORD]@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres?sslmode=require"
export SMM_PANEL_ADMIN_PASSWORD="강한관리자비밀번호"
export SMM_PANEL_SESSION_SECRET="충분히긴랜덤문자열"
python3 smm_panel/server.py --host 0.0.0.0 --port 8024
```

3. 서버 시작 로그에 `Storage backend: postgres` 가 보이면 Supabase DB 모드입니다.

주의할 점:
- 현재 환경에는 Postgres 드라이버가 기본 포함되어 있지 않으므로 `requirements.txt` 설치가 필요합니다.
- 운영에서는 Supabase 대시보드에서 제공하는 pooler 연결 문자열을 그대로 사용하는 편이 안전합니다.
- `service_role` 키는 DB 연결용이 아니라 REST/Auth/Storage 작업용이므로, 프런트로 내려주면 안 됩니다.

## Vercel 프런트 배포

이 저장소는 Vercel에서 정적 SPA 프런트와 `/api/*` Python 함수를 함께 배포할 수 있도록 `vercel.json`, `build-static.mjs`, `api/index.py` 를 포함합니다.

- 빌드 시 `static/index.html` 을 `dist/index.html` 로 복사합니다.
- `SMM_PANEL_PUBLIC_API_BASE_URL` 값이 있으면 빌드 단계에서 프런트 HTML 메타 태그에 주입합니다.
- `/api/*` 경로는 Python 함수로 전달되고, 나머지 일반 경로는 `index.html` 로 재작성됩니다.

Vercel 프로젝트에는 최소한 아래 환경변수를 설정하는 것을 권장합니다.

- `SMM_PANEL_SESSION_SECRET`: 세션 서명용 긴 랜덤 문자열
- `SMM_PANEL_ADMIN_PASSWORD`: 관리자 로그인 비밀번호
- `SMM_PANEL_DATABASE_URL`: Supabase/Postgres 연결 문자열

같은 Vercel 프로젝트에서 프런트와 `/api/*` 함수를 같이 배포하면 `SMM_PANEL_PUBLIC_API_BASE_URL` 은 비워 두면 됩니다. 별도 백엔드 프로젝트로 나눌 때만 `https://api.example.com` 같은 공개 주소를 넣으면 됩니다.
`SMM_PANEL_DATABASE_URL` 이 비어 있으면 Vercel 함수는 `/tmp/smm_panel.db` 임시 SQLite 로라도 부팅하지만, 이 경우 데이터는 영속되지 않으므로 실제 운영에서는 반드시 Supabase/Postgres 연결 문자열을 넣어야 합니다. 운영 환경에서는 `SMM_PANEL_SESSION_SECRET` 이 없으면 서버가 시작되지 않도록 강제됩니다.

## 권장 환경변수

- `SMM_PANEL_DATABASE_URL`: SQLite 대신 Supabase/Postgres 를 사용할 때의 연결 문자열
- `SMM_PANEL_SESSION_SECRET`: 세션 서명 비밀값
- `SMM_PANEL_PUBLIC_API_BASE_URL`: 프론트가 호출할 API 기본 주소
- `SMM_PANEL_ALLOWED_ORIGINS`: CORS 허용 Origin 목록
- `SMM_PANEL_PUBLIC_APP_ORIGIN`: 대표 프론트 Origin
- `SMM_PANEL_COOKIE_DOMAIN`: 관리자 세션 쿠키 공유 도메인
- `SMM_PANEL_ADMIN_COOKIE_SAMESITE`: `Strict`, `Lax`, `None`
- `SMM_PANEL_FORCE_SECURE_COOKIES`: HTTPS 강제 시 `true`

Supabase 관련 선택 환경변수:

- `SMM_PANEL_SUPABASE_URL`: 추후 Supabase Auth/Storage/Edge Functions 를 붙일 때 사용할 프로젝트 URL
- `SMM_PANEL_SUPABASE_DB_URL`: `SMM_PANEL_DATABASE_URL` 대신 사용할 별칭
- `SMM_PANEL_SUPABASE_ANON_KEY`: 공개 클라이언트 키가 필요한 기능을 백엔드에서 중계할 때만 사용
- `SMM_PANEL_SUPABASE_SERVICE_ROLE_KEY`: 절대 프론트로 내리지 말아야 하는 관리자 키
- `SMM_PANEL_GOOGLE_CLIENT_ID`, `SMM_PANEL_GOOGLE_CLIENT_SECRET`, `SMM_PANEL_GOOGLE_REDIRECT_URI`
- `SMM_PANEL_KAKAO_CLIENT_ID`, `SMM_PANEL_KAKAO_CLIENT_SECRET`, `SMM_PANEL_KAKAO_REDIRECT_URI`
- `SMM_PANEL_NAVER_CLIENT_ID`, `SMM_PANEL_NAVER_CLIENT_SECRET`, `SMM_PANEL_NAVER_REDIRECT_URI`

현재 소셜 로그인은 구조와 라우트, 고객 DB, 동의 이력 저장 흐름까지 준비되어 있고, 실제 OAuth 자격증명을 넣으면 연결 포인트를 이어서 완성할 수 있습니다.

운영에서는 `app.example.com` 과 `api.example.com` 처럼 같은 상위 도메인 아래에서 프론트와 API 를 나누는 구성을 추천합니다. 이렇게 하면 관리자 세션 쿠키를 상대적으로 안정적으로 유지할 수 있습니다.

## 주요 화면

- 홈: 블루 히어로, 플랫폼 탭, 배너 캐러셀, 추천 서비스, 공개 지원 허브
- 인증: 이메일 회원가입/로그인, 필수 약관 동의, 소셜 로그인 확장 포인트
- 주문: 모바일 우선 플랫폼 칩 + 상품 카드형 목록
- 상세: 옵션 칩, 동적 주문 폼, 요청 메모, 주의/환불/예상 소요시간
- 충전: 결제수단 안내, 거래 상태, 참조번호 포함 거래 내역
- 내역: 주문 상태별 필터와 카드형 주문 이력
- 마이: 계정/잔액/개인 주문 중심
- 도움말 허브: FAQ, 공지, 이용 가이드, 약관/정책

## DB 구조

핵심 테이블은 아래와 같습니다.

- `users`: 고객 기본 프로필, 계정 상태, 잔액, 등급, 마케팅 동의 상태
- `user_social_identities`: 이메일/소셜 로그인 식별자 매핑
- `user_consents`: 약관/개인정보/연령/마케팅 동의 이력
- `user_auth_tokens`: 이메일 인증/비밀번호 재설정 확장용 토큰 저장소
- `platform_sections`: 인스타그램/유튜브/웹툰 등 플랫폼 탭
- `platform_groups`: 플랫폼 내부 그룹
- `product_categories`: 상품 상세 페이지 단위
- `products`: 실제 주문 옵션 단위, 가격/수량 제한/폼 구조 JSON 포함
- `home_banners`, `home_interest_tags`, `home_spotlights`: 홈 화면 콘텐츠
- `support_links`, `benefits`, `notices`, `faqs`: 지원/안내 콘텐츠
- `orders`, `order_fields`: 주문 헤더와 입력 필드 스냅샷
- `balance_transactions`: 충전/주문 차감 내역
- `payment_records`: 결제수단/상태/참조번호/실패사유/관리자 조정 사유

`products.form_structure_json` 에 주문 폼 스키마를 JSON으로 저장해서, 상품마다 계정형/URL형/키워드형 폼을 다르게 렌더링합니다.
