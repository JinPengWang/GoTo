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
echo [1/6] Finding Python...

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
echo [2/6] Checking PyInstaller...

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
echo [3/6] Building exe (may take 1-2 minutes)...

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
rem Step 4: Backup registry and detect default browser
rem ==============================================
echo.
echo [4/6] Backing up registry and detecting default browser...

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
reg export "!PROG_CMD_KEY!" "!BACKUP_DIR!\default_browser_backup.reg" /y >nul 2>&1

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

echo   Backup complete.

rem ==============================================
rem Step 5: Register protocol handler
rem ==============================================
echo.
echo [5/6] Registering protocol handler...

set "NEW_CMD=\"!EXE_PATH!\" \"%%1\""

rem Method 1: Modify the default browser's ProgId command handler
rem This is what actually takes effect on Windows 10/11 due to UserChoice
reg add "!PROG_CMD_KEY!" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
if !errorlevel! neq 0 (
    echo   [WARNING] Failed to modify !PROG_ID! handler.
) else (
    echo   Modified: !PROG_ID!\shell\open\command
)

rem Method 2: Also set the generic http/https handlers (fallback)
reg add "HKEY_CLASSES_ROOT\http\shell\open\command" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
reg add "HKEY_CLASSES_ROOT\https\shell\open\command" /ve /t REG_SZ /d "!NEW_CMD!" /f >nul 2>&1
echo   Modified: http and https protocol handlers

echo   Done.

rem ==============================================
rem Step 6: Cleanup
rem ==============================================
echo.
echo [6/6] Cleaning up...
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
