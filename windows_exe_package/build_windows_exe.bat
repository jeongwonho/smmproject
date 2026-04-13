@echo off
setlocal

cd /d %~dp0

echo [1/5] Python version check
python --version
if errorlevel 1 (
  echo Python is not available.
  exit /b 1
)

echo [2/5] Creating virtual environment
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate
if errorlevel 1 (
  echo Failed to activate virtual environment.
  exit /b 1
)

echo [3/5] Installing build dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
if errorlevel 1 (
  echo Failed to install build dependencies.
  exit /b 1
)

echo [4/5] Building executable
pyinstaller --clean --noconfirm comment_brief_studio.spec
if errorlevel 1 (
  echo EXE build failed.
  exit /b 1
)

echo [5/5] Done
echo Output: %cd%\dist\comment_brief_studio.exe
endlocal
