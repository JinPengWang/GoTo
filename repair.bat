@echo off
setlocal enabledelayedexpansion

rem === Request admin if needed ===
net session >nul 2>&1
if !errorlevel! neq 0 (
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs -ArgumentList '%~dp0'"
    exit /b
)

if not "%~1"=="" (
    cd /d "%~1"
) else (
    cd /d "%~dp0"
)

echo.
echo ============================================================
echo   GoTo - Repair
echo ============================================================
echo.
echo   Working directory: %cd%
echo.

echo [1/5] Checking files...

if not exist "GoTo.exe" (
    echo.
    echo   [ERROR] GoTo.exe was not found.
    echo   It may have been deleted or quarantined by antivirus software.
    echo   Re-download the release package, then run install.bat.
    echo.
    pause
    exit /b 1
)

if not exist "rules.json" (
    echo.
    echo   [ERROR] rules.json was not found.
    echo   Re-download the release package or restore rules.json.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Get-Content -Raw -Encoding UTF8 -LiteralPath 'rules.json' | ConvertFrom-Json | Out-Null; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }"
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] rules.json is not valid JSON.
    echo.
    pause
    exit /b 1
)

set "EXE_PATH=%cd%\GoTo.exe"
echo   GoTo.exe is present.
echo   rules.json is valid.

echo.
echo [2/5] Detecting default browser...

set "PROG_ID="
for /f "tokens=3" %%a in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice" /v ProgId 2^>nul ^| findstr /i "ProgId"') do (
    set "PROG_ID=%%a"
)

if not defined PROG_ID (
    echo   [WARNING] Could not detect default browser ProgId.
    echo   Falling back to MSEdgeHTM.
    set "PROG_ID=MSEdgeHTM"
)

echo   Default browser ProgId: !PROG_ID!

echo.
echo [3/5] Re-registering GoTo...

set "PROG_CMD_KEY=HKEY_CLASSES_ROOT\!PROG_ID!\shell\open\command"
set "USER_PROG_CMD_KEY=HKCU\Software\Classes\!PROG_ID!\shell\open\command"
set "NEW_CMD=\"!EXE_PATH!\" \"%%1\""

reg add "!USER_PROG_CMD_KEY!" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Failed to write per-user browser handler.
    echo   Check Windows Security or antivirus protection history.
    echo.
    pause
    exit /b 1
)

reg add "!PROG_CMD_KEY!" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
reg add "HKEY_CLASSES_ROOT\http\shell\open\command" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
reg add "HKEY_CLASSES_ROOT\https\shell\open\command" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1

echo   Re-registered protocol handler.

echo.
echo [4/5] Checking QQ and WeChat...

set "APP_CONFIGURED=0"
reg query "HKCU\Software\Tencent\QQ" >nul 2>&1
if !errorlevel! equ 0 (
    reg add "HKCU\Software\Tencent\QQ" /v UseDefaultBrowser /t REG_DWORD /d 1 /f >nul 2>&1
    echo   Configured: QQ
    set /a APP_CONFIGURED+=1
)

reg query "HKCU\Software\Tencent\QQNT" >nul 2>&1
if !errorlevel! equ 0 (
    reg add "HKCU\Software\Tencent\QQNT" /v UseDefaultBrowser /t REG_DWORD /d 1 /f >nul 2>&1
    echo   Configured: QQNT
    set /a APP_CONFIGURED+=1
)

reg query "HKCU\Software\Tencent\WeChat" >nul 2>&1
if !errorlevel! equ 0 (
    reg add "HKCU\Software\Tencent\WeChat" /v UseDefaultBrowser /t REG_DWORD /d 1 /f >nul 2>&1
    echo   Configured: WeChat
    set /a APP_CONFIGURED+=1
)

if !APP_CONFIGURED! equ 0 echo   QQ and WeChat not found.

echo.
echo [5/5] Health check...

set "CURRENT_CMD="
for /f "tokens=2*" %%a in ('reg query "!USER_PROG_CMD_KEY!" /ve 2^>nul ^| findstr /ve "HKEY"') do (
    set "CURRENT_CMD=%%b"
)

echo !CURRENT_CMD! | findstr /i /c:"GoTo.exe" >nul
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Registry still does not point to GoTo.exe.
    echo   Actual: !CURRENT_CMD!
    echo.
    pause
    exit /b 1
)

echo   Registry handler points to GoTo.exe.
echo.
echo ============================================================
echo.
echo   REPAIR COMPLETE
echo.
echo   If links still do not route, restart the app you clicked links from.
echo   If GoTo.exe disappears again, check Windows Security protection history.
echo.
pause
