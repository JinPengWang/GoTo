@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ============================================================
echo   GoTo - Go Native Build (Ultra-Fast)
echo ============================================================
echo.
echo   Working directory: %cd%
echo.

rem ==============================================
rem Step 1: Check Go Environment
rem ==============================================
echo [1/5] Checking Go compiler...

set "GO_CMD="
for /f "tokens=*" %%P in ('where go.exe 2^>nul') do (
    if not defined GO_CMD set "GO_CMD=%%P"
)

if not defined GO_CMD (
    if exist "C:\Program Files\Go\bin\go.exe" set "GO_CMD=C:\Program Files\Go\bin\go.exe"
)

if not defined GO_CMD (
    echo.
    echo   [ERROR] Go compiler (go.exe) was not found in PATH or C:\Program Files\Go\bin.
    echo   Please install Go from https://go.dev/dl/ and try again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('"!GO_CMD!" version 2^>^&1') do set "GOVER=%%i"
echo   Found: !GOVER!

rem ==============================================
rem Step 2: Download dependencies
rem ==============================================
echo.
echo [2/5] Downloading dependencies...

"!GO_CMD!" mod tidy
if !errorlevel! neq 0 (
    echo.
    echo   [WARNING] go mod tidy returned non-zero, continuing build...
)

rem ==============================================
rem Step 3: Run Go Unit Tests
rem ==============================================
echo.
echo [3/5] Running Go unit tests...

"!GO_CMD!" test -v ./...
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Go unit tests failed! Fix tests before building.
    echo.
    pause
    exit /b 1
)
echo   All Go unit tests passed.

rem ==============================================
rem Step 4: Build Ultra-Fast Native Binary
rem ==============================================
echo.
echo [4/5] Compiling GoTo.exe (Windows GUI, -s -w optimized)...

"!GO_CMD!" build -ldflags="-H=windowsgui -s -w" -o "GoTo.exe" .
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Go compilation failed.
    echo.
    pause
    exit /b 1
)

for %%A in ("GoTo.exe") do set "EXESIZE=%%~zA"
set /a "EXESIZE_KB=!EXESIZE! / 1024"
echo   Built: %cd%\GoTo.exe (!EXESIZE_KB! KB)

rem ==============================================
rem Step 5: Generate Checksum
rem ==============================================
echo.
echo [5/5] Generating SHA256SUMS.txt...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$files = 'GoTo.exe','rules.json','install.bat','uninstall.bat','repair.bat','README.md','README.en.md','LICENSE'; $files | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { $h = Get-FileHash -Algorithm SHA256 -LiteralPath $_; '{0}  {1}' -f $h.Hash.ToLower(), $_ } | Set-Content -Encoding ascii -LiteralPath 'SHA256SUMS.txt'"
if !errorlevel! neq 0 (
    echo   [WARNING] Could not generate SHA256SUMS.txt.
) else (
    echo   Wrote: SHA256SUMS.txt
)

echo.
echo ============================================================
echo   GO NATIVE BUILD SUCCESSFUL
echo ============================================================
echo.
echo   Binary size:  !EXESIZE_KB! KB
echo   Startup time: ~2-5 ms (Zero extraction lag)
echo.
pause
