@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ============================================================
echo   GoTo - Developer Build
echo ============================================================
echo.
echo   Working directory: %cd%
echo.

rem ==============================================
rem Step 1: Find Python
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
    echo.
    echo   [ERROR] Python 3.8+ was not found.
    echo   Install Python, then run build.bat again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('"!PYTHON!" --version 2^>^&1') do set "PYVER=%%i"
echo   Found: !PYVER!
echo   Path: !PYTHON!

rem ==============================================
rem Step 2: Validate source files
rem ==============================================
echo.
echo [2/6] Validating source files...

if not exist "redirector.py" (
    echo   [ERROR] redirector.py not found.
    pause
    exit /b 1
)

if not exist "rules.json" (
    echo   [ERROR] rules.json not found.
    pause
    exit /b 1
)

"!PYTHON!" -m json.tool "rules.json" >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] rules.json is not valid JSON.
    "!PYTHON!" -m json.tool "rules.json"
    echo.
    pause
    exit /b 1
)

"!PYTHON!" -m py_compile "redirector.py"
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] redirector.py failed Python syntax validation.
    echo.
    pause
    exit /b 1
)

echo   Source files are valid.

rem ==============================================
rem Step 3: Check PyInstaller
rem ==============================================
echo.
echo [3/6] Checking PyInstaller...

"!PYTHON!" -c "import PyInstaller" >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] PyInstaller is not installed in this Python environment.
    echo.
    echo   Install it manually, then run build.bat again:
    echo     "!PYTHON!" -m pip install -r requirements-build.txt
    echo.
    echo   If PyPI SSL fails, use a trusted mirror or offline wheel.
    echo   install.bat never installs build dependencies on user machines.
    echo.
    pause
    exit /b 1
)

echo   PyInstaller is available.

rem ==============================================
rem Step 4: Build exe
rem ==============================================
echo.
echo [4/6] Building GoTo.exe...

if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "GoTo.spec" del /f /q "GoTo.spec"

set "VERSION_FLAG="
if exist "version_info.txt" set "VERSION_FLAG=--version-file version_info.txt"

"!PYTHON!" -m PyInstaller --onefile --noconsole --name GoTo --clean --noconfirm !VERSION_FLAG! redirector.py
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Build failed.
    echo.
    pause
    exit /b 1
)

copy /y "dist\GoTo.exe" "GoTo.exe" >nul
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Could not copy dist\GoTo.exe to project root.
    echo.
    pause
    exit /b 1
)

echo   Built: %cd%\GoTo.exe

rem ==============================================
rem Step 5: Generate checksum
rem ==============================================
echo.
echo [5/6] Generating SHA256SUMS.txt...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$files = 'GoTo.exe','rules.json','install.bat','uninstall.bat','repair.bat'; $files | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { $h = Get-FileHash -Algorithm SHA256 -LiteralPath $_; '{0}  {1}' -f $h.Hash.ToLower(), $_ } | Set-Content -Encoding ascii -LiteralPath 'SHA256SUMS.txt'"
if !errorlevel! neq 0 (
    echo   [WARNING] Could not generate SHA256SUMS.txt.
) else (
    echo   Wrote: SHA256SUMS.txt
)

rem ==============================================
rem Step 6: Finish
rem ==============================================
echo.
echo [6/6] Done.
echo.
echo   Build complete. To create a user package, include:
echo     GoTo.exe
echo     rules.json
echo     install.bat
echo     uninstall.bat
echo     repair.bat
echo     SHA256SUMS.txt
echo.
pause
