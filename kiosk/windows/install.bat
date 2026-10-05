@echo off
rem Installe le lancement automatique d'un module a l'ouverture de session Windows.
rem Usage : install.bat module1
set MODULE=%1
if "%MODULE%"=="" set MODULE=module1
set LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\BIP2026 %MODULE%.lnk
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%');$s.TargetPath='%~dp0kiosk.bat';$s.Arguments='%MODULE%';$s.WindowStyle=7;$s.Save()"
rem Pas de mise en veille de l'ecran
powercfg /change monitor-timeout-ac 0
powercfg /change standby-timeout-ac 0
echo OK : %MODULE% demarrera a la prochaine ouverture de session.
pause
