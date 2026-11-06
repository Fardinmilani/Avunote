@echo off
setlocal
title Avunote - Build Setup
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_setup.ps1" %*
set "avunote_build_exit=%errorlevel%"
echo.
if "%avunote_build_exit%"=="0" (
  echo Build command finished successfully.
) else (
  echo Build failed. Read the message above and the log in .local\build-logs.
)
if not "%AVUNOTE_BUILD_NO_PAUSE%"=="1" if not "%VOXRIVA_BUILD_NO_PAUSE%"=="1" pause
exit /b %avunote_build_exit%
