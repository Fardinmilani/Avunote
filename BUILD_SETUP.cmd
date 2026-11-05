@echo off
setlocal
title Voxriva - Build Setup
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_setup.ps1" %*
set "voxriva_build_exit=%errorlevel%"
echo.
if "%voxriva_build_exit%"=="0" (
  echo Build command finished successfully.
) else (
  echo Build failed. Read the message above and the log in .local\build-logs.
)
if not "%VOXRIVA_BUILD_NO_PAUSE%"=="1" pause
exit /b %voxriva_build_exit%
