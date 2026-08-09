@echo off
setlocal EnableExtensions
echo === DRIVES ===
wmic logicaldisk get name,volumename,drivetype 2>nul
echo.
echo === SEARCH python*.exe / py.exe depth^<=4 ===
for %%D in (C D E F G H) do (
  if exist %%D:\ (
    echo --- %%D: ---
    call :scan0 %%D
  )
)
echo === DONE ===
goto :eof

:scan0
if exist "%~1:\python.exe" echo %~1:\python.exe
if exist "%~1:\python3.exe" echo %~1:\python3.exe
if exist "%~1:\pythonw.exe" echo %~1:\pythonw.exe
if exist "%~1:\py.exe" echo %~1:\py.exe
for /d %%A in ("%~1:\*") do call :scan1 "%%~fA"
goto :eof

:scan1
if exist "%~1\python.exe" echo %~1\python.exe
if exist "%~1\python3.exe" echo %~1\python3.exe
if exist "%~1\pythonw.exe" echo %~1\pythonw.exe
if exist "%~1\py.exe" echo %~1\py.exe
for /d %%B in ("%~1\*") do call :scan2 "%%~fB"
goto :eof

:scan2
if exist "%~1\python.exe" echo %~1\python.exe
if exist "%~1\python3.exe" echo %~1\python3.exe
if exist "%~1\pythonw.exe" echo %~1\pythonw.exe
if exist "%~1\py.exe" echo %~1\py.exe
for /d %%C in ("%~1\*") do call :scan3 "%%~fC"
goto :eof

:scan3
if exist "%~1\python.exe" echo %~1\python.exe
if exist "%~1\python3.exe" echo %~1\python3.exe
if exist "%~1\pythonw.exe" echo %~1\pythonw.exe
if exist "%~1\py.exe" echo %~1\py.exe
for /d %%E in ("%~1\*") do call :scan4 "%%~fE"
goto :eof

:scan4
if exist "%~1\python.exe" echo %~1\python.exe
if exist "%~1\python3.exe" echo %~1\python3.exe
if exist "%~1\pythonw.exe" echo %~1\pythonw.exe
if exist "%~1\py.exe" echo %~1\py.exe
goto :eof
