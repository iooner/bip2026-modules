@echo off
rem Lance le pont Kinect et le relance en cas d arret.
if not exist "%~dp0KinectBridge.exe" call "%~dp0build.bat"
:loop
"%~dp0KinectBridge.exe"
timeout /t 3 /nobreak >nul
goto loop
