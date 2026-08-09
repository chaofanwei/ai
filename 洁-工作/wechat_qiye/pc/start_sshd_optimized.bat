@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Win7 SSH + Tunnel

set "SSHDIR=E:\OpenSSH-Win64"
set "PORT=2222"
set "LOG=%SSHDIR%\sshd.log"
set "CONFIG=%SSHDIR%\sshd_config"
set "PIDFILE=C:\ProgramData\ssh\sshd.pid"
set "MAX_RETRY=5"
set "LISTEN_WAIT=12"

cd /d "%SSHDIR%"

echo ========================================
echo   Win7 SSH + reverse tunnel
echo ========================================
echo.

echo [0] Cleanup old sshd / free port %PORT% ...
taskkill /f /im sshd.exe >nul 2>&1

REM wait until port is not LISTENING
set /a free_wait=0
:wait_port_free
netstat -an | findstr ":%PORT%" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 goto port_free
set /a free_wait+=1
if !free_wait! GEQ 15 (
    echo [WARN] port %PORT% still busy, continue anyway
    goto port_free
)
ping -n 2 127.0.0.1 >nul
goto wait_port_free
:port_free

if exist "%PIDFILE%" del /f /q "%PIDFILE%" >nul 2>&1

set /a attempt=0
:start_sshd
set /a attempt+=1
echo [1] Start sshd port %PORT% attempt !attempt!/%MAX_RETRY% ...

if exist "%LOG%" del /f /q "%LOG%" >nul 2>&1

REM same start style as original bat; more reliable on Win7
start /b E:\OpenSSH-Win64\sshd.exe -D -f E:\OpenSSH-Win64\sshd_config -e > E:\OpenSSH-Win64\sshd.log 2>&1

set /a poll=0
:poll_listen
ping -n 2 127.0.0.1 >nul
netstat -an | findstr ":%PORT%" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [OK] sshd listening on %PORT%
    goto start_tunnel
)
tasklist /fi "IMAGENAME eq sshd.exe" | findstr /i "sshd.exe" >nul 2>&1
if errorlevel 1 (
    echo [FAIL] sshd process exited
    goto retry_sshd
)
set /a poll+=1
if !poll! LSS %LISTEN_WAIT% goto poll_listen

echo [FAIL] port %PORT% not listening after wait

:retry_sshd
if exist "%LOG%" (
    echo ---- sshd.log ----
    type "%LOG%"
    echo -----------------
)
taskkill /f /im sshd.exe >nul 2>&1
if exist "%PIDFILE%" del /f /q "%PIDFILE%" >nul 2>&1
if !attempt! LSS %MAX_RETRY% (
    ping -n 3 127.0.0.1 >nul
    goto start_sshd
)

echo [FAIL] sshd failed after %MAX_RETRY% attempts, see %LOG%
pause
exit /b 1

:start_tunnel
echo.
echo [2] Start reverse tunnel 3311 -^> 127.0.0.1:%PORT% ...

REM kill old tunnel to same host if any
for /f "tokens=2 delims=," %%P in ('wmic process where "Name='ssh.exe' and CommandLine like '%%47.121.185.35%%'" get ProcessId /format:csv 2^>nul ^| findstr /r "[0-9]"') do (
    taskkill /f /pid %%P >nul 2>&1
)

start "SSH-Tunnel" cmd /c "E:\OpenSSH-Win64\ssh.exe -N -R 3311:127.0.0.1:2222 -i %USERPROFILE%\.ssh\id_win7 -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes root@47.121.185.35"

ping -n 3 127.0.0.1 >nul

echo.
echo ========================================
echo  Done
echo  Local sshd: 0.0.0.0:%PORT%
echo  Remote: 47.121.185.35:3311 -^> local
echo  Log: %LOG%
echo.
echo  On Linux server:
echo  ssh -p 3311 -i ~/.ssh/id_win7 bidcenter\xs0409@127.0.0.1
echo ========================================
echo.
pause
exit /b 0
