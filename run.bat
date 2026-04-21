@echo off
setlocal
where pwsh >nul 2>nul
if %errorlevel%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run.ps1" %*
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run.ps1" %*
)
if not %errorlevel%==0 (
  echo.
  echo run.bat failed. Please keep this window open and send the red error text to the developer.
  pause
)
endlocal
