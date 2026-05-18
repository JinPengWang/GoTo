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
echo     - Restore the original browser handler
echo     - Remove QQ and WeChat browser configuration
echo     - Delete the exe and build artifacts
echo.
set /p "CONFIRM=   Proceed? (Y/N): "
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
echo [1/5] Reading install metadata...

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
echo [2/5] Restoring registry...

set "RESTORED=0"

rem Try to restore the default browser ProgId handler
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

    rem First try: restore from .reg backup file
    if exist "!BACKUP_DIR!\default_browser_backup.reg" (
        reg import "!BACKUP_DIR!\default_browser_backup.reg" >nul 2>&1
        if !errorlevel! equ 0 (
            echo   Restored: !PROG_ID! handler from backup file
            set /a RESTORED+=1
        )
    )

    rem Second try: set the original command directly
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

rem Restore generic http/https handlers
if exist "!BACKUP_DIR!\http_backup.reg" (
    reg import "!BACKUP_DIR!\http_backup.reg" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Restored: http handler
        set /a RESTORED+=1
    )
)

if exist "!BACKUP_DIR!\https_backup.reg" (
    reg import "!BACKUP_DIR!\https_backup.reg" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Restored: https handler
        set /a RESTORED+=1
    )
)

if !RESTORED! equ 0 (
    echo.
    echo   [WARNING] No backups could be restored.
    echo   Please set your default browser manually:
    echo     Settings -^> Apps -^> Default Apps -^> Web Browser
)

rem ==============================================
rem Step 3: Remove QQ and WeChat browser configuration
rem ==============================================
echo.
echo [3/5] Removing QQ and WeChat configuration...

set "APP_CLEANED=0"

rem QQ
reg query "HKCU\Software\Tencent\QQ" /v UseDefaultBrowser >nul 2>&1
if !errorlevel! equ 0 (
    reg delete "HKCU\Software\Tencent\QQ" /v UseDefaultBrowser /f >nul 2>&1
    echo   Removed: QQ UseDefaultBrowser
    set /a APP_CLEANED+=1
)

rem QQNT
reg query "HKCU\Software\Tencent\QQNT" /v UseDefaultBrowser >nul 2>&1
if !errorlevel! equ 0 (
    reg delete "HKCU\Software\Tencent\QQNT" /v UseDefaultBrowser /f >nul 2>&1
    echo   Removed: QQNT UseDefaultBrowser
    set /a APP_CLEANED+=1
)

rem WeChat
reg query "HKCU\Software\Tencent\WeChat" /v UseDefaultBrowser >nul 2>&1
if !errorlevel! equ 0 (
    reg delete "HKCU\Software\Tencent\WeChat" /v UseDefaultBrowser /f >nul 2>&1
    echo   Removed: WeChat UseDefaultBrowser
    set /a APP_CLEANED+=1
)

if !APP_CLEANED! equ 0 (
    echo   No QQ/WeChat configuration found.
)

rem ==============================================
rem Step 4: Delete program files
rem ==============================================
echo.
echo [4/5] Removing program files...

if exist "GoTo.exe" (
    del /f /q "GoTo.exe"
    echo   Deleted: GoTo.exe
) else (
    echo   GoTo.exe not found, skipping.
)

if exist "redirector.spec" del /f /q "redirector.spec"

rem ==============================================
rem Step 5: Cleanup
rem ==============================================
echo.
echo [5/5] Cleaning up...

if exist "build" rd /s /q "build" && echo   Deleted: build/
if exist "dist" rd /s /q "dist" && echo   Deleted: dist/
if exist "__pycache__" rd /s /q "__pycache__" && echo   Deleted: __pycache__/
if exist "!BACKUP_DIR!" rd /s /q "!BACKUP_DIR!" && echo   Deleted: backup/

echo   Cleanup done.

echo.
echo ============================================================
echo.
echo   UNINSTALLATION COMPLETE
echo.
echo   GoTo has been removed.
echo.
echo   If links stop working, please set your default browser:
echo     Settings -^> Apps -^> Default Apps -^> Web Browser
echo.
echo   Thank you for using GoTo!
echo.
pause
