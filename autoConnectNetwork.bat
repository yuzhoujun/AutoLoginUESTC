@echo off
rem ============================================================
rem  UESTC campus network auto login -- double click to run.
rem
rem  Pure PowerShell, no Python required.
rem  Default: log in once and exit.
rem  For a long-running daemon that reconnects when the link
rem  drops, change -Once below to -Daemon.
rem
rem  NOTE: this file is ASCII on purpose. Chinese comments in a
rem  .bat break cmd.exe parsing on a GBK console, so the
rem  Chinese documentation lives in README.md instead.
rem ============================================================
cd /d "%~dp0"

set "PS=powershell.exe"
rem If PowerShell is not found, or you want to pin the 64-bit
rem one explicitly, uncomment the next line:
rem set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0uestc-login.ps1" -Once

echo.
echo Exit code: %ERRORLEVEL%
pause
