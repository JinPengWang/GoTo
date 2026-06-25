@echo off
setlocal enabledelayedexpansion

rem ============================================================
rem  GoTo - Silent self-healing script
rem ============================================================
rem  Runs via Task Scheduler to keep GoTo registration alive.
rem  No admin rights required (writes to HKCU only).
rem  No output, no pauses — completely silent.
rem ============================================================

cd /d "%~dp0"

rem Exit if GoTo.exe is missing
if not exist "GoTo.exe" exit /b 1

rem Detect current default browser ProgId
set "PROG_ID="
for /f "tokens=3" %%a in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice" /v ProgId 2^>nul ^| findstr /i "ProgId"') do (
    set "PROG_ID=%%a"
)
if not defined PROG_ID set "PROG_ID=MSEdgeHTM"

set "EXE_PATH=%cd%\GoTo.exe"
set "NEW_CMD=\"!EXE_PATH!\" \"%%1\""

rem Check if per-user handler is already correct
set "USER_PROG_CMD_KEY=HKCU\Software\Classes\!PROG_ID!\shell\open\command"
set "CURRENT_CMD="
for /f "tokens=2*" %%a in ('reg query "!USER_PROG_CMD_KEY!" /ve 2^>nul ^| findstr /ve "HKEY"') do (
    set "CURRENT_CMD=%%b"
)

rem If handler already points to GoTo, nothing to do
echo !CURRENT_CMD! | findstr /i /c:"GoTo.exe" >nul
if !errorlevel! equ 0 exit /b 0

rem Re-register: per-user handler (no admin needed)
reg add "!USER_PROG_CMD_KEY!" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1

rem Also try system-wide handlers (best-effort, may need admin)
set "PROG_CMD_KEY=HKEY_CLASSES_ROOT\!PROG_ID!\shell\open\command"
reg add "!PROG_CMD_KEY!" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
reg add "HKEY_CLASSES_ROOT\http\shell\open\command" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
reg add "HKEY_CLASSES_ROOT\https\shell\open\command" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1

exit /b 0
