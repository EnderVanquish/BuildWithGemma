@echo off
REM Argus launcher for cmd.exe / double-click. Delegates to run.ps1, which holds the
REM actual configuration -- keeping one source of truth rather than two drifting copies.
REM
REM   run.bat            start and open the dashboard
REM   run.bat status     RAM / CPU / tokens-per-sec / recent observations
REM   run.bat logs       follow container output
REM   run.bat stop       remove the container
REM   run.bat build      rebuild the image
REM
REM -ExecutionPolicy Bypass is scoped to this one process, so it does not change any
REM machine or user policy -- it only stops an unsigned local script being blocked.

setlocal
set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=start"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" -Action %ACTION% %2 %3 %4 %5 %6 %7 %8 %9
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo Argus exited with code %RC%.
  REM Only pause when double-clicked; pausing inside a script or CI would hang it.
  echo %CMDCMDLINE% | find /i "%~0" >nul && pause
)

endlocal & exit /b %RC%
