# Brand Grid Studio

브랜드 해석, 단품 시안 생성, 9/12 그리드 기획, 리뷰, ZIP 내보내기를 한 번에 처리하는 내부망용 인스타그램 제작 스튜디오입니다.

현재 버전은 `Python 단일 서버 + 정적 프론트엔드 + SQLite + 백그라운드 작업 큐` 구조로 구성되어 있습니다. 기본 라우트는 `mock` 렌더러로 동작하고, 서버 환경에 `GOOGLE_API_KEY`가 있으면 `gemini` 라우트로 전환할 수 있습니다.

## 포함 기능

- 프로젝트/브리프 저장
- Brand Pack 자동 분석
- Reference Pack / Lock 규칙 생성
- 단품 시안 생성
- 9 / 12 슬롯 그리드 기획과 슬롯별 재생성
- 핀 코멘트 기반 리뷰
- ZIP / Contact Sheet / JSON 내보내기
- 내부 IP 전용 접근 제한

## 실행

로컬에서 브라우저까지 같이 열기:

```bash
python3 desktop_app.py
```

내부망에서 접속 가능하게 서버 실행:

```bash
python3 server.py --host 0.0.0.0 --port 8010
```

기본 정책은 사설망 / loopback IP만 허용합니다. 필요하면 추가 허용 대역을 지정할 수 있습니다.

```bash
python3 server.py --host 0.0.0.0 --port 8010 --allow-cidr 100.64.0.0/10
```

## 모델 라우팅

`studio_data/settings.json` 에서 Draft / Final / Photo Quality 라우트의 provider, model, cost 를 조정할 수 있습니다.

- 기본값: 전부 `mock`
- `provider=gemini` 로 바꾸면 서버는 `GOOGLE_API_KEY` 환경변수를 사용해 이미지를 생성하려고 시도합니다.
- 키가 없거나 호출이 실패하면 자동으로 Mock 렌더러로 폴백합니다.

예시:

```bash
export GOOGLE_API_KEY="..."
python3 server.py --host 0.0.0.0 --port 8010
```

## 저장 구조

- `studio_data/brand_grid_studio.db`: 프로젝트/버전/코멘트/작업 메타데이터
- `studio_data/assets/`: 업로드 참조 이미지와 생성 결과물
- `studio_data/exports/`: ZIP 패키지와 Contact Sheet
- `studio_data/settings.json`: 비용/모델 라우팅 설정

## 성능 포인트

- SQLite WAL 모드 사용
- 이미지 업로드 시 브라우저에서 먼저 축소/팔레트 추출
- 생성은 백그라운드 작업 큐로 처리
- 정적 파일과 메타데이터를 분리해 로컬 서버 반응성을 유지
- 내부 IP guard 로 외부 접근을 차단

## 현재 제약

- Mock 렌더러 모드에서는 결과물이 SVG 기반 미리보기 자산으로 생성됩니다.
- 실제 래스터 이미지는 `gemini` 라우트가 활성화되어야 생성됩니다.
- URL 요약은 내부망/대상 사이트 정책에 따라 실패할 수 있으므로 수동 참조 이미지와 함께 쓰는 것을 권장합니다.

## 문서

- 구현/배포 계획: [docs/implementation_plan.md](/Users/bug/Documents/New%20project/docs/implementation_plan.md)

