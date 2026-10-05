@echo off
rem Lance un module en kiosk plein ecran et le relance s'il se ferme ou plante.
rem Usage : kiosk.bat module1
set MODULE=%1
if "%MODULE%"=="" set MODULE=module1
set ROOT=%~dp0..\..
for %%I in ("%ROOT%") do set ROOT=%%~fI
set URL=file:///%ROOT:\=/%/%MODULE%/index.html
rem Module avec serveur local (ex. module2 : relais des cameras IP, port 8360 par defaut)
if exist "%ROOT%\%MODULE%\server.py" (
  start "bip2026-server" /min python "%ROOT%\%MODULE%\server.py"
  set URL=http://127.0.0.1:8360/index.html
)
set PROFILE=%LOCALAPPDATA%\bip2026-kiosk-%MODULE%

set BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe
if not exist "%BROWSER%" set BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe
if not exist "%BROWSER%" set BROWSER=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe
if not exist "%BROWSER%" set BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe

:loop
start "" /wait "%BROWSER%" --kiosk --kiosk-printing --noerrdialogs --disable-infobars ^
  --disable-pinch --overscroll-history-navigation=0 --disable-session-crashed-bubble ^
  --autoplay-policy=no-user-gesture-required ^
  --disable-features=Translate --no-first-run --user-data-dir="%PROFILE%" "%URL%"
timeout /t 2 /nobreak >nul
goto loop
