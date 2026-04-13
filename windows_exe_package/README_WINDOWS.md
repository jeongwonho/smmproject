# Windows EXE 패키지 폴더

이 폴더는 `댓글 브리프 스튜디오`를 Windows에서 `.exe` 로 빌드하기 위한 전용 구조입니다.

## 폴더 구조

- `app/desktop_app.py`
  로컬 실행형 메인 앱
- `app/server.py`
  댓글 수집, 요약, 저장 로직
- `build_windows_exe.bat`
  Windows에서 `.exe` 빌드용 배치 파일
- `comment_brief_studio.spec`
  PyInstaller 빌드 설정
- `requirements-build.txt`
  빌드용 의존성
- `dist/`
  빌드 후 `.exe` 가 생성될 위치
- `output/`
  실행 결과 파일 저장 위치

## Windows에서 EXE 만들기

1. Windows PC에서 이 폴더를 그대로 복사합니다.
2. 터미널 또는 PowerShell에서 이 폴더로 이동합니다.
3. `build_windows_exe.bat` 를 실행합니다.
4. 완료 후 `dist\comment_brief_studio.exe` 를 확인합니다.

## 주의

- 현재 작업 머신은 macOS이므로, 여기서는 Windows용 실제 `.exe` 를 직접 생성할 수 없습니다.
- 이 폴더는 Windows에서 바로 빌드 가능한 형태로 미리 구성한 것입니다.
- 앱은 콘솔형 EXE로 빌드됩니다. 실행 후 터미널에서 질문에 답하며 사용할 수 있습니다.
