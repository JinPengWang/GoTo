@echo off
setlocal enabledelayedexpansion

rem === Request admin if needed ===
net session >nul 2>&1
if !errorlevel! neq 0 (
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs -ArgumentList '%~dp0'"
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
echo   GoTo - Uninstaller
echo ============================================================
echo.
echo   This will:
echo     - Restore the original default browser protocol handler
echo     - Remove QQ and WeChat browser configuration overrides
echo     - Remove GoTo scheduled maintenance tasks
echo.
set /p "CONFIRM=   Proceed with uninstallation? (Y/N): "
if /i not "!CONFIRM!"=="Y" (
    echo.
    echo   Cancelled.
    pause
    exit /b 0
)

echo.

rem ==============================================
rem Step 1: Read metadata from install
rem ==============================================
echo [1/4] Reading install metadata...

set "BACKUP_DIR=%cd%\backup"
set "META_FILE=!BACKUP_DIR!\metadata.txt"
set "PROG_ID="
set "ORIG_CMD="
set "EXE_PATH="
set "USER_OVERRIDE_BACKED_UP=0"

if exist "!META_FILE!" (
    for /f "usebackq tokens=1,* delims==" %%a in ("!META_FILE!") do (
        if "%%a"=="PROG_ID" set "PROG_ID=%%b"
        if "%%a"=="ORIG_CMD" set "ORIG_CMD=%%b"
        if "%%a"=="EXE_PATH" set "EXE_PATH=%%b"
        if "%%a"=="USER_OVERRIDE_BACKED_UP" set "USER_OVERRIDE_BACKED_UP=%%b"
    )
    echo   Found metadata.
    echo   ProgId: !PROG_ID!
    if defined ORIG_CMD echo   Original command: !ORIG_CMD!
) else (
    echo   No metadata file found.
    echo   Will try to restore from registry backup files.
)

rem ==============================================
rem Step 2: Restore registry
rem ==============================================
echo.
echo [2/4] Restoring registry...

set "RESTORED=0"

if defined PROG_ID (
    set "PROG_CMD_KEY=HKEY_CLASSES_ROOT\!PROG_ID!\shell\open\command"
    set "USER_PROG_CMD_KEY=HKCU\Software\Classes\!PROG_ID!\shell\open\command"

    rem Restore or remove the per-user override created during install.
    if "!USER_OVERRIDE_BACKED_UP!"=="1" (
        if exist "!BACKUP_DIR!\user_default_browser_backup.reg" (
            reg import "!BACKUP_DIR!\user_default_browser_backup.reg" >nul 2>&1
            if !errorlevel! equ 0 (
                echo   Restored: per-user !PROG_ID! handler from backup file
                set /a RESTORED+=1
            )
        )
    ) else (
        set "USER_CMD="
        for /f "tokens=2*" %%a in ('reg query "!USER_PROG_CMD_KEY!" /ve 2^>nul ^| findstr /ve "HKEY"') do (
            set "USER_CMD=%%b"
        )
        if defined USER_CMD (
            echo !USER_CMD! | findstr /i /c:"GoTo.exe" >nul
            if !errorlevel! equ 0 (
                reg delete "!USER_PROG_CMD_KEY!" /f >nul 2>&1
                if !errorlevel! equ 0 (
                    echo   Removed: per-user !PROG_ID! handler
                    set /a RESTORED+=1
                )
            )
        )
    )

    rem Restore HKCR from .reg backup file
    if exist "!BACKUP_DIR!\default_browser_backup.reg" (
        reg import "!BACKUP_DIR!\default_browser_backup.reg" >nul 2>&1
        if !errorlevel! equ 0 (
            echo   Restored: !PROG_ID! handler from backup file
            set /a RESTORED+=1
        )
    )

    rem Fallback: set the original command directly
    if !RESTORED! equ 0 (
        if defined ORIG_CMD (
            reg add "!PROG_CMD_KEY!" /ve /t REG_SZ /d "!ORIG_CMD!" /f >nul 2>&1
            if !errorlevel! equ 0 (
                echo   Restored: !PROG_ID! handler to original command
                set /a RESTORED+=1
            )
        )
    )
)

if !RESTORED! equ 0 (
    echo.
    echo   [WARNING] Could not automatically restore registry.
    echo   Please verify your default browser in Windows Settings:
    echo     Settings -^> Apps -^> Default Apps -^> Web Browser
)

rem ==============================================
rem Step 3: Remove scheduled maintenance tasks
rem ==============================================
echo.
echo [3/4] Removing scheduled tasks...

schtasks /delete /tn "GoTo-Maintain" /f >nul 2>&1
if !errorlevel! equ 0 (
    echo   Removed: GoTo-Maintain
) else (
    echo   GoTo-Maintain task not found or already removed.
)

schtasks /delete /tn "GoTo-Maintain-Scheduled" /f >nul 2>&1
if !errorlevel! equ 0 (
    echo   Removed: GoTo-Maintain-Scheduled
) else (
    echo   GoTo-Maintain-Scheduled task not found or already removed.
)

rem ==============================================
rem Step 4: Remove QQ and WeChat browser configuration
rem ==============================================
echo.
echo [4/4] Removing QQ and WeChat configuration...

set "APP_CLEANED=0"

reg query "HKCU\Software\Tencent\QQ" /v UseDefaultBrowser >nul 2>&1
if !errorlevel! equ 0 (
    reg delete "HKCU\Software\Tencent\QQ" /v UseDefaultBrowser /f >nul 2>&1
    echo   Removed: QQ UseDefaultBrowser
    set /a APP_CLEANED+=1
)

reg query "HKCU\Software\Tencent\QQNT" /v UseDefaultBrowser >nul 2>&1
if !errorlevel! equ 0 (
    reg delete "HKCU\Software\Tencent\QQNT" /v UseDefaultBrowser /f >nul 2>&1
    echo   Removed: QQNT UseDefaultBrowser
    set /a APP_CLEANED+=1
)

reg query "HKCU\Software\Tencent\WeChat" /v UseDefaultBrowser >nul 2>&1
if !errorlevel! equ 0 (
    reg delete "HKCU\Software\Tencent\WeChat" /v UseDefaultBrowser /f >nul 2>&1
    echo   Removed: WeChat UseDefaultBrowser
    set /a APP_CLEANED+=1
)

if !APP_CLEANED! equ 0 (
    echo   No QQ/WeChat override configuration found.
)

echo.
echo ============================================================
echo   UNINSTALLATION COMPLETE
echo ============================================================
echo.
echo   GoTo system hooks and tasks have been removed.
echo   Your rules.json and program files were preserved.
echo   If you wish to completely remove GoTo, you may now delete this folder.
echo.
pause
