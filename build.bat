@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ============================================================
echo   GoTo - Smart Builder (Go Native / Python Fallback)
echo ============================================================
echo.
echo   Working directory: %cd%
echo.

rem ==============================================
rem Check for Go compiler first
rem ==============================================
set "GO_CMD="
if exist "C:\Program Files\Go\bin\go.exe" set "GO_CMD=C:\Program Files\Go\bin\go.exe"

if "!GO_CMD!"=="" (
    for /f "delims=" %%i in ('where.exe go.exe 2^>nul') do (
        if exist "%%i" set "GO_CMD=%%i"
    )
)

if not "!GO_CMD!"=="" goto :BUILD_GO
goto :BUILD_PYTHON

:BUILD_GO
echo [FOUND] Go compiler detected: !GO_CMD!
for /f "tokens=*" %%i in ('"!GO_CMD!" version 2^>^&1') do echo   Version: %%i
echo.
echo ------------------------------------------------------------
echo   Building Go Native Binary - Ultra Fast
echo ------------------------------------------------------------
echo.

echo [1/4] Downloading Go dependencies...
"!GO_CMD!" mod tidy >nul 2>&1

echo [2/4] Running Go unit tests...
"!GO_CMD!" test -v ./...
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Go unit tests failed! Fix tests before building.
    pause
    exit /b 1
)

echo [3/4] Compiling GoTo.exe...
"!GO_CMD!" build -ldflags="-H=windowsgui -s -w" -o "GoTo.exe" .
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Go compilation failed.
    pause
    exit /b 1
)

for %%A in ("GoTo.exe") do set "EXESIZE=%%~zA"
set /a "EXESIZE_KB=!EXESIZE! / 1024"
echo   Built: %cd%\GoTo.exe [!EXESIZE_KB! KB]

goto :GENERATE_CHECKSUM

:BUILD_PYTHON
echo [INFO] Go compiler not detected. Using Python build pipeline...
echo.

set "PYTHON="
if exist "C:\Program Files\Python312\python.exe" set "PYTHON=C:\Program Files\Python312\python.exe"

if "!PYTHON!"=="" (
    for /f "delims=" %%i in ('where.exe python.exe 2^>nul') do (
        if "!PYTHON!"=="" if exist "%%i" set "PYTHON=%%i"
    )
)
if "!PYTHON!"=="" (
    for /f "delims=" %%i in ('where.exe python3.exe 2^>nul') do (
        if "!PYTHON!"=="" if exist "%%i" set "PYTHON=%%i"
    )
)

if "!PYTHON!"=="" (
    echo.
    echo   [ERROR] Neither Go nor Python 3.8+ was found.
    echo   Please install Go https://go.dev/ or Python.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('"!PYTHON!" --version 2^>^&1') do set "PYVER=%%i"
echo   Found Python: !PYVER!

echo [1/4] Validating source files...
if not exist "redirector.py" (
    echo   [ERROR] redirector.py not found.
    pause
    exit /b 1
)
"!PYTHON!" -m json.tool "rules.json" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [ERROR] rules.json is not valid JSON.
    pause
    exit /b 1
)

echo [2/4] Running Python unit tests...
"!PYTHON!" -m unittest discover -s tests -p "test_*.py" -v
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Python unit tests failed!
    pause
    exit /b 1
)

echo [3/4] Building GoTo.exe via PyInstaller...
"!PYTHON!" -c "import PyInstaller" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [ERROR] PyInstaller is not installed in Python environment.
    echo   Run: "!PYTHON!" -m pip install -r requirements-build.txt
    pause
    exit /b 1
)

if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "GoTo.spec" del /f /q "GoTo.spec"

set "VERSION_FLAG="
if exist "version_info.txt" set "VERSION_FLAG=--version-file version_info.txt"

"!PYTHON!" -m PyInstaller --onefile --noconsole --name GoTo --clean --noconfirm !VERSION_FLAG! redirector.py
if !errorlevel! neq 0 (
    echo   [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

copy /y "dist\GoTo.exe" "GoTo.exe" >nul
for %%A in ("GoTo.exe") do set "EXESIZE=%%~zA"
set /a "EXESIZE_KB=!EXESIZE! / 1024"
echo   Built: %cd%\GoTo.exe [!EXESIZE_KB! KB]

:GENERATE_CHECKSUM
echo.
echo [4/4] Generating SHA256SUMS.txt...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$files = 'GoTo.exe','rules.json','install.bat','uninstall.bat','repair.bat','README.md','README.en.md','LICENSE'; $files | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { $h = Get-FileHash -Algorithm SHA256 -LiteralPath $_; '{0}  {1}' -f $h.Hash.ToLower(), $_ } | Set-Content -Encoding ascii -LiteralPath 'SHA256SUMS.txt'"
if !errorlevel! neq 0 (
    echo   [WARNING] Could not generate SHA256SUMS.txt.
) else (
    echo   Wrote: SHA256SUMS.txt
)

echo.
echo ============================================================
echo   BUILD COMPLETE
echo ============================================================
echo.
echo   GoTo.exe is ready in the current folder.
echo.
