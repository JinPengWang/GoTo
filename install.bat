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
echo   GoTo - Installer
echo ============================================================
echo.
echo   Working directory: %cd%
echo.

rem ==============================================
rem Step 1: Find a working Python
rem ==============================================
echo [1/7] Finding Python...

set "PYTHON="

for /f "tokens=*" %%P in ('where python.exe 2^>nul') do (
    if not defined PYTHON (
        "%%P" --version >nul 2>&1
        if !errorlevel! equ 0 set "PYTHON=%%P"
    )
)

if not defined PYTHON (
    for /f "tokens=*" %%P in ('where python3.exe 2^>nul') do (
        if not defined PYTHON (
            "%%P" --version >nul 2>&1
            if !errorlevel! equ 0 set "PYTHON=%%P"
        )
    )
)

if not defined PYTHON (
    echo   Trying common install locations...
    for %%P in (
        "%ProgramFiles%\Python312\python.exe"
        "%ProgramFiles%\Python311\python.exe"
        "%ProgramFiles%\Python310\python.exe"
        "%ProgramFiles%\Python39\python.exe"
        "%LocalAppData%\Programs\Python\Python312\python.exe"
        "%LocalAppData%\Programs\Python\Python311\python.exe"
        "%LocalAppData%\Programs\Python\Python310\python.exe"
        "%LocalAppData%\Programs\Python\Python39\python.exe"
    ) do (
        if not defined PYTHON (
            if exist %%P (
                %%P --version >nul 2>&1
                if !errorlevel! equ 0 set "PYTHON=%%~P"
            )
        )
    )
)

if not defined PYTHON (
    echo   Searching registry...
    for /f "tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\Python\PythonCore" /s /v ExecutablePath 2^>nul ^| findstr /i "ExecutablePath"') do (
        if not defined PYTHON (
            if exist "%%b" (
                "%%b" --version >nul 2>&1
                if !errorlevel! equ 0 set "PYTHON=%%b"
            )
        )
    )
)

if not defined PYTHON (
    echo.
    echo   [ERROR] No working Python found!
    echo   Install Python 3.8+ from https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('"!PYTHON!" --version 2^>^&1') do set "PYVER=%%i"
echo   Found: !PYVER!
echo   Path: !PYTHON!

rem ==============================================
rem Step 2: Install PyInstaller
rem ==============================================
echo.
echo [2/7] Checking PyInstaller...

"!PYTHON!" -c "import PyInstaller" >nul 2>&1
if !errorlevel! neq 0 (
    echo   Installing PyInstaller via pip...
    "!PYTHON!" -m pip install pyinstaller
    if !errorlevel! neq 0 (
        echo.
        echo   [ERROR] PyInstaller installation failed!
        echo   Try manually: "!PYTHON!" -m pip install pyinstaller
        echo.
        pause
        exit /b 1
    )
    echo   PyInstaller installed.
) else (
    echo   PyInstaller already installed.
)

rem ==============================================
rem Step 3: Build exe
rem ==============================================
echo.
echo [3/8] Validating configuration...

if not exist "redirector.py" (
    echo   [ERROR] redirector.py not found in %cd%
    pause
    exit /b 1
)

if not exist "rules.json" (
    echo   [ERROR] rules.json not found in %cd%
    pause
    exit /b 1
)

"!PYTHON!" -m json.tool "rules.json" >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] rules.json is not valid JSON.
    echo   Fix the configuration file before installing.
    echo   Details:
    "!PYTHON!" -m json.tool "rules.json"
    echo.
    pause
    exit /b 1
)
echo   rules.json is valid.

rem ==============================================
rem Step 4: Build exe
rem ==============================================
echo.
echo [4/8] Building exe (may take 1-2 minutes)...

if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "redirector.spec" del /f /q "redirector.spec"

"!PYTHON!" -m PyInstaller --onefile --noconsole --name GoTo --clean --noconfirm redirector.py

if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Build failed! See output above.
    pause
    exit /b 1
)

if exist "GoTo.exe" del /f /q "GoTo.exe"
copy "dist\GoTo.exe" "." >nul

set "EXE_PATH=%cd%\GoTo.exe"
echo.
echo   Build success: !EXE_PATH!

rem ==============================================
rem Step 5: Backup registry and detect default browser
rem ==============================================
echo.
echo [5/8] Backing up registry and detecting default browser...

set "BACKUP_DIR=%cd%\backup"
if not exist "!BACKUP_DIR!" mkdir "!BACKUP_DIR!"

rem Backup the generic http/https handlers
reg export "HKEY_CLASSES_ROOT\http\shell\open\command" "!BACKUP_DIR!\http_backup.reg" /y >nul 2>&1
reg export "HKEY_CLASSES_ROOT\https\shell\open\command" "!BACKUP_DIR!\https_backup.reg" /y >nul 2>&1

rem Detect the current default browser ProgId from UserChoice
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

rem Backup the original command for this ProgId
set "PROG_CMD_KEY=HKEY_CLASSES_ROOT\!PROG_ID!\shell\open\command"
set "USER_PROG_CMD_KEY=HKCU\Software\Classes\!PROG_ID!\shell\open\command"
set "USER_OVERRIDE_BACKED_UP=0"
reg export "!PROG_CMD_KEY!" "!BACKUP_DIR!\default_browser_backup.reg" /y >nul 2>&1
reg export "!USER_PROG_CMD_KEY!" "!BACKUP_DIR!\user_default_browser_backup.reg" /y >nul 2>&1
if !errorlevel! equ 0 set "USER_OVERRIDE_BACKED_UP=1"

rem Also read the original command value for later reference
set "ORIG_CMD="
for /f "tokens=2*" %%a in ('reg query "!PROG_CMD_KEY!" /ve 2^>nul ^| findstr /ve "HKEY"') do (
    set "ORIG_CMD=%%b"
)

if defined ORIG_CMD (
    echo   Original command: !ORIG_CMD!
) else (
    echo   [WARNING] Could not read original command.
)

rem Save metadata for uninstall
echo PROG_ID=!PROG_ID!> "!BACKUP_DIR!\metadata.txt"
echo ORIG_CMD=!ORIG_CMD!>> "!BACKUP_DIR!\metadata.txt"
echo EXE_PATH=!EXE_PATH!>> "!BACKUP_DIR!\metadata.txt"
echo USER_OVERRIDE_BACKED_UP=!USER_OVERRIDE_BACKED_UP!>> "!BACKUP_DIR!\metadata.txt"

echo   Backup complete.

rem ==============================================
rem Step 6: Register protocol handler
rem ==============================================
echo.
echo [6/8] Registering protocol handler...

set "NEW_CMD=\"!EXE_PATH!\" \"%%1\""

rem Method 1: Add a per-user ProgId override.
rem HKCR merges HKCU before HKLM, so browser updates are less likely to overwrite this.
reg add "!USER_PROG_CMD_KEY!" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
if !errorlevel! neq 0 (
    echo   [WARNING] Failed to modify per-user !PROG_ID! handler.
) else (
    echo   Modified: HKCU\Software\Classes\!PROG_ID!\shell\open\command
)

rem Method 2: Modify the machine/default browser ProgId command handler
reg add "!PROG_CMD_KEY!" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
if !errorlevel! neq 0 (
    echo   [WARNING] Failed to modify !PROG_ID! handler.
) else (
    echo   Modified: !PROG_ID!\shell\open\command
)

rem Method 3: Also set the generic http/https handlers (fallback)
reg add "HKEY_CLASSES_ROOT\http\shell\open\command" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
reg add "HKEY_CLASSES_ROOT\https\shell\open\command" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
echo   Modified: http and https protocol handlers

echo   Done.

rem ==============================================
rem Step 7: Configure QQ and WeChat to use external browser
rem ==============================================
echo.
echo [7/8] Configuring QQ and WeChat...

set "APP_CONFIGURED=0"

rem QQ: set UseDefaultBrowser = 1
reg query "HKCU\Software\Tencent\QQ" >nul 2>&1
if !errorlevel! equ 0 (
    reg add "HKCU\Software\Tencent\QQ" /v UseDefaultBrowser /t REG_DWORD /d 1 /f >nul 2>&1
    echo   Configured: QQ (UseDefaultBrowser = 1)
    set /a APP_CONFIGURED+=1
)

rem QQNT: set UseDefaultBrowser = 1
reg query "HKCU\Software\Tencent\QQNT" >nul 2>&1
if !errorlevel! equ 0 (
    reg add "HKCU\Software\Tencent\QQNT" /v UseDefaultBrowser /t REG_DWORD /d 1 /f >nul 2>&1
    echo   Configured: QQNT (UseDefaultBrowser = 1)
    set /a APP_CONFIGURED+=1
)

rem WeChat: set UseDefaultBrowser = 1
reg query "HKCU\Software\Tencent\WeChat" >nul 2>&1
if !errorlevel! equ 0 (
    reg add "HKCU\Software\Tencent\WeChat" /v UseDefaultBrowser /t REG_DWORD /d 1 /f >nul 2>&1
    echo   Configured: WeChat (UseDefaultBrowser = 1)
    set /a APP_CONFIGURED+=1
)

if !APP_CONFIGURED! equ 0 (
    echo   QQ and WeChat not found (no action needed).
) else (
    echo   Note: Some links in QQ/WeChat may still use the built-in browser.
    echo   If so, enable "Open links with default browser" in app settings.
)

rem ==============================================
rem Step 8: Cleanup
rem ==============================================
echo.
echo [8/8] Cleaning up...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "redirector.spec" del /f /q "redirector.spec"
echo   Done.

echo.
echo ============================================================
echo.
echo   INSTALLATION COMPLETE
echo.
echo   GoTo is now active.
echo   It intercepts ALL link opens and routes them:
echo.
echo     GitHub, Google, YouTube, etc.  --> Chrome
echo     Baidu, Bilibili, Taobao, etc.  --> Edge
echo     edge:// pages                   --> Edge (direct)
echo.
echo   Config:  %cd%\rules.json
echo   Logs:    %%APPDATA%%\GoTo\logs\
echo   Backup:  !BACKUP_DIR!\
echo.
echo   Edit rules.json to change rules (takes effect immediately).
echo   Run uninstall.bat to remove and restore original settings.
echo.
pause
