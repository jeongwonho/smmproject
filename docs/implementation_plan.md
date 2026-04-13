# Brand Grid Studio 구현 계획

## 1. MVP 범위

PRD의 v1 핵심을 아래 다섯 축으로 고정했다.

- Brand Pack
- Create One
- Grid Planner (9 / 12)
- Review Board
- Model Router / Cost Guard / Export

범용 생성기나 자유 노드 캔버스는 넣지 않고, 내부 제작팀이 빨리 정답에 도달하는 워크플로우를 우선한다.

## 2. 아키텍처

### 프론트엔드

- 정적 HTML / CSS / JavaScript
- 왼쪽: 프로젝트/브리프
- 중앙: Brand Pack / Create One / Grid Planner / Review
- 오른쪽: Queue / Settings / 내부망 접속 정보

### 백엔드

- Python `ThreadingHTTPServer`
- SQLite(WAL) 기반 메타데이터 저장
- SVG 목업 렌더러 + Gemini 옵션 라우팅
- 백그라운드 작업 큐로 생성 작업 분리

### 저장소 구조

- DB: 프로젝트, variants, comments, jobs
- Assets: 참조 이미지, 생성 이미지
- Exports: ZIP, contact sheet, summary JSON

## 3. 내부망 배포 전략

### 기본 운영

- `127.0.0.1` 로 로컬 실행
- 내부 공유 시 `0.0.0.0` bind
- 사설 IP / loopback 외 요청은 차단

### 추천 운영 형태

1. 사내 PC 또는 미니 서버에 `python3 server.py --host 0.0.0.0 --port 8010`
2. 내부 DNS 또는 고정 IP 연결
3. 운영용 계정에 `GOOGLE_API_KEY` 환경변수 설정
4. 필요 시 리버스 프록시에서 TLS 종료

## 4. 성능 최적화 포인트

- SQLite WAL: 읽기/쓰기 충돌 완화
- 브라우저 업로드 전 축소: 대용량 참조 이미지 비용 절감
- 백그라운드 큐: 생성 요청이 UI를 막지 않음
- Mock / Gemini 이중 라우팅: 운영 전 테스트 속도 확보
- Grid regeneration: 잠금 슬롯 유지 후 필요한 칸만 재생성

## 5. 기능별 구현 상태

### 완료

- 프로젝트 생성/수정
- Brand Pack 자동 분석
- Tone / Palette / Lock 규칙 시각화
- 단품 시안 생성
- 9 / 12 Grid Planner
- 슬롯 단위 선택/잠금/재생성
- 핀 코멘트 리뷰
- ZIP 내보내기
- 라우트 설정 UI
- 내부 IP guard

### 후속 권장

- 실제 Gemini / Imagen 모델별 응답 파싱 강화
- 프로젝트 권한/사용자 인증
- 승인 로그 / 감사 로그
- 배치 큐 분리(Redis/Celery 등)
- PNG/JPG/WebP 서버측 래스터화 파이프라인

## 6. 운영 메모

- Mock 모드는 워크플로우 검증용이다.
- 실운영 고해상도 결과물은 Gemini 라우트 활성화가 전제다.
- 의료/금융 등 규제 업종은 금지어 사전과 검수 규칙을 별도 강화하는 것이 좋다.
