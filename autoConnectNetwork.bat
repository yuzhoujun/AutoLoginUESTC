@echo off
rem ============================================================
rem  UESTC campus network auto login - Windows launcher
rem
rem  Double-click to open the menu. You can also pass any
rem  command that manage.py accepts:
rem
rem      autoConnectNetwork.bat once             login once
rem      autoConnectNetwork.bat run              run in foreground
rem      autoConnectNetwork.bat install          register autostart
rem      autoConnectNetwork.bat uninstall        remove autostart
rem      autoConnectNetwork.bat status           show status
rem
rem  ------------------------------------------------------------------
rem  WHY THIS FILE IS PURE ASCII
rem
rem  A .bat containing non-ASCII text cannot be made to work reliably.
rem  Saved as UTF-8, a GBK console executes the Chinese fragments as
rem  commands (they are not valid command names). Saved as GBK, the
rem  same file shows as garbage on a UTF-8 console. Neither encoding is
rem  safe, because the console code page is not under our control.
rem
rem  So all Chinese text lives in the Python scripts. Python 3.6+ writes
rem  to the Windows console through the Unicode API and is therefore
rem  rendered correctly under every code page. This file only forwards.
rem  ------------------------------------------------------------------
rem ============================================================

setlocal EnableExtensions
cd /d "%~dp0"

rem Commands that need administrator rights (registering / removing
rem scheduled tasks and services). Keep in sync with manage.py.
set "NEED_ADMIN="
if /i "%~1"=="install"           set "NEED_ADMIN=1"
if /i "%~1"=="uninstall"         set "NEED_ADMIN=1"
if /i "%~1"=="start"             set "NEED_ADMIN=1"
if /i "%~1"=="stop"              set "NEED_ADMIN=1"
if /i "%~1"=="install-service"   set "NEED_ADMIN=1"
if /i "%~1"=="uninstall-service" set "NEED_ADMIN=1"

rem ---- locate a usable Python interpreter --------------------------
rem
rem Two traps here, both of which occur on real machines:
rem
rem 1. "python" on PATH is often the Microsoft Store placeholder in
rem    %LOCALAPPDATA%\Microsoft\WindowsApps. It executes nothing and
rem    returns 9009. So never trust the name -- always probe it.
rem
rem 2. A working interpreter is not enough; it also needs the
rem    "requests" package. msys64 ships a python without it.
rem
rem So each candidate is probed twice: once for "import requests"
rem (good), once for "import sys" (usable, but warn about the missing
rem dependency). PYTHON overrides everything.

set "PY="
set "PY_FALLBACK="

if defined PYTHON call :try "%PYTHON%"

rem Written by "manage.py install"; lets later double-clicks work even
rem if PATH changes. See :try for the format.
set "PY_FILE="
if exist "%~dp0python-path.txt" set /p PY_FILE=<"%~dp0python-path.txt"
if defined PY_FILE call :try "%PY_FILE%"

if defined CONDA_PREFIX call :try "%CONDA_PREFIX%\python.exe"

call :try python
call :try py

for %%D in (
    "%ProgramData%\anaconda3"
    "%ProgramData%\miniconda3"
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\miniconda3"
    "%LOCALAPPDATA%\Programs\Python\Python313"
    "%LOCALAPPDATA%\Programs\Python\Python312"
    "D:\APP-D\anaconda3"
) do call :try "%%~D\python.exe"

if not defined PY if defined PY_FALLBACK set "PY=%PY_FALLBACK%" && set "PY_WARN=1"

if not defined PY (
    echo.
    echo [!] No usable Python found.
    echo.
    echo     This project needs Python 3.11 or newer, with "requests".
    echo     Install it, or point PYTHON at your python.exe:
    echo.
    echo         set PYTHON=D:\APP-D\anaconda3\python.exe
    echo         autoConnectNetwork.bat
    echo.
    echo     Conda note: a bare "python" may resolve to the Microsoft
    echo     Store placeholder, which does nothing and returns 9009.
    echo     Use an absolute path to avoid it.
    echo.
    echo     Tried: PYTHON, python-path.txt, CONDA_PREFIX, python, py,
    echo            and the usual anaconda / miniconda locations.
    echo.
    pause
    exit /b 9009
)

if defined PY_WARN (
    echo.
    echo [!] Using %PY%
    echo     but "import requests" failed for it. If the run below
    echo     reports a missing module, install the dependency:
    echo         %PY% -m pip install requests
    echo.
)

rem ---- elevate when the requested command needs it ---------------
rem
rem Only admin commands trigger the UAC prompt, so "once" and "run"
rem stay a plain double-click with no prompt.

net session >nul 2>&1
if errorlevel 1 if defined NEED_ADMIN (
    echo Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs" >nul 2>nul
    if errorlevel 1 (
        echo.
        echo [!] Elevation was cancelled or failed.
        echo     Right-click this file and pick "Run as administrator".
        echo.
        pause
    )
    exit /b
)

rem ---- forward to manage.py --------------------------------------

%PY% "%~dp0manage.py" %*
set "RC=%ERRORLEVEL%"

rem An elevated window closes on exit, taking the output with it.
rem Keep it open after admin commands so the result can be read.
if defined NEED_ADMIN (
    echo.
    echo Exit code: %RC%
    pause
)

endlocal & exit /b %RC%


rem ============================================================
rem  :try <candidate>
rem
rem  Probe one interpreter. %1 may be a bare command ("python") or a
rem  quoted absolute path. Records the first candidate that can
rem  "import requests" in PY, and the first that merely runs in
rem  PY_FALLBACK.
rem ============================================================
:try
%1 -c "import requests" >nul 2>nul
if not errorlevel 1 if not defined PY set "PY=%1"
%1 -c "import sys" >nul 2>nul
if not errorlevel 1 if not defined PY_FALLBACK set "PY_FALLBACK=%1"
goto :eof
