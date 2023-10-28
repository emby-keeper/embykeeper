@echo off

where powershell >nul 2>nul
if not %errorlevel% == 0 (
    echo Powershell 不可用, 您需要安装 Powershell 以使用该软件.
    (((echo.%cmdcmdline%)|find /I "%~0")>nul) && pause
    exit /b 1
)
if not exist "%~dp0/python-*-embed-*" (
    echo **************************************************
    echo *            请等待, 正在下载 Embykeeper         *
    echo **************************************************
    powershell Unblock-File -Path '%~dp0downloaders\download_python.ps1'
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0downloaders\download_python.ps1" -Version 3.8.10 -TargetDirectory "." || goto :error
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0downloaders\download_pip.ps1" -TargetDirectory "python-3.8.10-embed-amd64" || goto :error
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0downloaders\download_deps.ps1" -RequirementsFile "%~dp0script\requirements.txt" -PipPath "%~dp0python-3.8.10-embed-amd64\Scripts\pip.exe" || goto :error
    xcopy /y "%~dp0script\Update.bat" "%~dp0"
    echo **************************************************
    echo 安装完成! 即将启动 Embykeeper.
    timeout /t 2 /nobreak > NUL
    cls
)
echo **************************************************
echo.
"%~dp0/python-3.8.10-embed-amd64/python.exe" "script\cli.py"
echo.
echo **************************************************
(((echo.%cmdcmdline%)|find /I "%~0")>nul) && echo | set /p="Embykeeper 已结束, 请按任意键退出..." & pause>nul

goto :EOF

:error
echo **************************************************
echo 发生错误, 即将退出, 请反馈以上信息.
(((echo.%cmdcmdline%)|find /I "%~0")>nul) && pause
