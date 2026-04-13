# Pulse24 Demo Panel

`mkt24.net`의 정보 구조와 모바일 우선 흐름을 참고해 제작한 데모용 SMM 패널입니다.  
브랜드명, 문구, 배너 자산은 그대로 복제하지 않고, `홈 → 상품목록 → 상품상세 → 충전 → 주문내역 → 마이` UX와 플랫폼/카테고리/상품/주문 DB 구조를 별도 구현했습니다.

## 실행

```bash
python3 smm_panel/server.py --host 127.0.0.1 --port 8024
```

브라우저에서 `http://127.0.0.1:8024` 로 접속하면 됩니다.

## 구성

- 백엔드: Python 표준 라이브러리 HTTP 서버 + SQLite
- 프론트엔드: 정적 HTML/CSS/Vanilla JS SPA
- 저장소: `smm_panel/data/smm_panel.db`

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
