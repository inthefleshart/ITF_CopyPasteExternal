@echo off
REM ============================================================
REM  build_zbrush_exes.bat
REM  Compiles the ZBrush OBJ <-> ODVertexData helper scripts
REM  into standalone Windows executables using PyInstaller.
REM
REM  Run this from the repo root after activating the venv:
REM    .venv\Scripts\activate
REM    build_zbrush_exes.bat
REM ============================================================

echo Building ZBrush helper executables...

set SRC_DIR=ZBrush\ODCopyPaste\source
set OUT_DIR=ZBrush\ODCopyPaste

REM Build objToVertData.exe
pyinstaller --distpath "%OUT_DIR%" --noupx --onefile "%SRC_DIR%\objToVertData.py"
if errorlevel 1 (
    echo ERROR: Failed to build objToVertData.exe
    exit /b 1
)

REM Build vertDataToObj.exe
pyinstaller --distpath "%OUT_DIR%" --noupx --onefile "%SRC_DIR%\vertDataToObj.py"
if errorlevel 1 (
    echo ERROR: Failed to build vertDataToObj.exe
    exit /b 1
)

REM Clean up PyInstaller build artefacts
if exist build rmdir /s /q build
if exist objToVertData.spec del objToVertData.spec
if exist vertDataToObj.spec del vertDataToObj.spec

echo.
echo Done! Executables written to: %OUT_DIR%
echo   - objToVertData.exe
echo   - vertDataToObj.exe
