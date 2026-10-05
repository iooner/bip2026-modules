@echo off
rem Compile KinectBridge.exe avec le compilateur C# inclus dans Windows (.NET Framework 4.5+).
rem Prerequis : Kinect for Windows SDK 1.8 installe.
set CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe
if not exist "%CSC%" set CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe
set KDLL=%KINECTSDK10_DIR%Assemblies\Microsoft.Kinect.dll
if not exist "%KDLL%" set KDLL=%ProgramFiles%\Microsoft SDKs\Kinect\v1.8\Assemblies\Microsoft.Kinect.dll
if not exist "%KDLL%" (echo Kinect SDK 1.8 introuvable. & pause & exit /b 1)
copy /y "%KDLL%" "%~dp0" >nul
"%CSC%" /nologo /optimize /out:"%~dp0KinectBridge.exe" /r:"%KDLL%" "%~dp0KinectBridge.cs"
if errorlevel 1 (pause & exit /b 1)
echo OK : KinectBridge.exe
