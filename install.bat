@echo off
setlocal enabledelayedexpansion

rem === Request admin if needed ===
net session >nul 2>&1
if !errorlevel! neq 0 (
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs -ArgumentList '%~dp0'"
    exit /b
)

rem === If launched with argument, use it as working dir ===
if not "%~1"=="" (
    cd /d "%~1"
) else (
    cd /d "%~dp0"
)

echo.
echo ============================================================
echo   GoTo - Installer
echo ============================================================
echo.
echo   Working directory: %cd%
echo.

rem ==============================================
rem Step 1: Validate release package
rem ==============================================
echo [1/7] Validating package...

if not exist "GoTo.exe" (
    echo.
    echo   [ERROR] GoTo.exe was not found.
    echo.
    echo   This installer is for the release package, which must include:
    echo     GoTo.exe
    echo     rules.json
    echo     install.bat
    echo     uninstall.bat
    echo.
    echo   If you downloaded source code, run build.bat first or download
    echo   the release zip from the project Releases page.
    echo.
    pause
    exit /b 1
)

if not exist "rules.json" (
    echo.
    echo   [ERROR] rules.json was not found.
    echo   Re-download the release package and try again.
    echo.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Get-Content -Raw -Encoding UTF8 -LiteralPath 'rules.json' | ConvertFrom-Json | Out-Null; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }"
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] rules.json is not valid JSON.
    echo   Fix or replace rules.json before installing.
    echo.
    pause
    exit /b 1
)

set "EXE_PATH=%cd%\GoTo.exe"
echo   GoTo.exe: !EXE_PATH!
echo   rules.json is valid.

rem ==============================================
rem Step 2: Detect current default browser
rem ==============================================
echo.
echo [2/7] Detecting default browser...

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

rem ==============================================
rem Step 3: Backup registry
rem ==============================================
echo.
echo [3/7] Backing up registry...

set "BACKUP_DIR=%cd%\backup"
if not exist "!BACKUP_DIR!" mkdir "!BACKUP_DIR!"

set "PROG_CMD_KEY=HKEY_CLASSES_ROOT\!PROG_ID!\shell\open\command"
set "USER_PROG_CMD_KEY=HKCU\Software\Classes\!PROG_ID!\shell\open\command"
set "USER_OVERRIDE_BACKED_UP=0"

reg export "!PROG_CMD_KEY!" "!BACKUP_DIR!\default_browser_backup.reg" /y >nul 2>&1
reg export "!USER_PROG_CMD_KEY!" "!BACKUP_DIR!\user_default_browser_backup.reg" /y >nul 2>&1
if !errorlevel! equ 0 set "USER_OVERRIDE_BACKED_UP=1"

set "ORIG_CMD="
for /f "tokens=2*" %%a in ('reg query "!PROG_CMD_KEY!" /ve 2^>nul ^| findstr /ve "HKEY"') do (
    set "ORIG_CMD=%%b"
)

echo PROG_ID=!PROG_ID!> "!BACKUP_DIR!\metadata.txt"
echo ORIG_CMD=!ORIG_CMD!>> "!BACKUP_DIR!\metadata.txt"
echo EXE_PATH=!EXE_PATH!>> "!BACKUP_DIR!\metadata.txt"
echo USER_OVERRIDE_BACKED_UP=!USER_OVERRIDE_BACKED_UP!>> "!BACKUP_DIR!\metadata.txt"
echo INSTALLED_AT=%date% %time%>> "!BACKUP_DIR!\metadata.txt"

echo   Backup directory: !BACKUP_DIR!

rem ==============================================
rem Step 4: Register protocol handler
rem ==============================================
echo.
echo [4/7] Registering protocol handler...

set "NEW_CMD=\"!EXE_PATH!\" \"%%1\""
set "REGISTER_ERRORS=0"

rem HKCR merges HKCU before HKLM, so this survives browser updates better.
reg add "!USER_PROG_CMD_KEY!" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
if !errorlevel! neq 0 (
    echo   [WARNING] Failed to modify per-user !PROG_ID! handler.
    set /a REGISTER_ERRORS+=1
) else (
    echo   Modified: HKCU\Software\Classes\!PROG_ID!\shell\open\command
)

rem Keep the old HKCR write as a compatibility fallback.
reg add "!PROG_CMD_KEY!" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
if !errorlevel! neq 0 (
    echo   [WARNING] Failed to modify !PROG_ID! handler.
) else (
    echo   Modified: !PROG_ID!\shell\open\command
)

if !REGISTER_ERRORS! neq 0 (
    echo.
    echo   [ERROR] Could not write the primary registry handler.
    echo   Try running install.bat again, or check Windows Security history.
    echo.
    pause
    exit /b 1
)

rem ==============================================
rem Step 5: Configure QQ and WeChat
rem ==============================================
echo.
echo [5/7] Configuring QQ and WeChat...

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

if !APP_CONFIGURED! equ 0 (
    echo   QQ and WeChat not found (or will use system default).
) else (
    echo   External links from QQ/WeChat configured to use default browser.
)

rem ==============================================
rem Step 6: Health check
rem ==============================================
echo.
echo [6/7] Running health check...

if not exist "!EXE_PATH!" (
    echo.
    echo   [ERROR] GoTo.exe disappeared after registration.
    echo   Check Windows Security protection history or antivirus quarantine.
    echo.
    pause
    exit /b 1
)

set "CURRENT_CMD="
for /f "tokens=2*" %%a in ('reg query "!USER_PROG_CMD_KEY!" /ve 2^>nul ^| findstr /ve "HKEY"') do (
    set "CURRENT_CMD=%%b"
)

echo !CURRENT_CMD! | findstr /i /c:"GoTo.exe" >nul
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Registry health check failed.
    echo   Expected per-user handler to point to GoTo.exe.
    echo   Actual: !CURRENT_CMD!
    echo.
    pause
    exit /b 1
)

echo   Registry handler points to GoTo.exe.
echo   GoTo.exe is present.

rem ==============================================
rem Step 7: Set up automatic maintenance
rem ==============================================
echo.
echo [7/7] Setting up automatic maintenance...

rem Create scheduled task: run at user logon (1 min delay)
schtasks /create /tn "GoTo-Maintain" /tr "\"\"!EXE_PATH!\" --maintain\"" /sc onlogon /delay 0001:00 /rl limited /f >nul 2>&1
if !errorlevel! equ 0 (
    echo   Created task: GoTo-Maintain (at logon)
) else (
    echo   [WARNING] Failed to create logon task.
)

rem Create scheduled task: run every 4 hours
schtasks /create /tn "GoTo-Maintain-Scheduled" /tr "\"\"!EXE_PATH!\" --maintain\"" /sc hourly /mo 4 /rl limited /f >nul 2>&1
if !errorlevel! equ 0 (
    echo   Created task: GoTo-Maintain-Scheduled (every 4 hours)
) else (
    echo   [WARNING] Failed to create periodic task.
)

echo.
echo ============================================================
echo   INSTALLATION COMPLETE
echo ============================================================
echo.
echo   GoTo is now active.
echo.
echo   Config:  %cd%\rules.json
echo   Logs:    %%APPDATA%%\GoTo\logs\ or %cd%\logs\
echo   Backup:  !BACKUP_DIR!\
echo.
echo   Test routing anytime:
echo     GoTo.exe --test "https://github.com"
echo.
echo   If GoTo stops working, run repair.bat.
echo   Run uninstall.bat to remove and restore original settings.
echo.
pause
