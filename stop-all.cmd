@echo off
setlocal
net session >nul 2>&1
if %errorlevel%==0 (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-all.ps1" %*
  exit /b %errorlevel%
)

powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File','%~dp0stop-all.ps1')"
exit /b %errorlevel%
