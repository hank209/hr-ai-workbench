@echo off
cd /d "%~dp0"
echo ============================================
echo   人事工作台 正在启动，请稍候...
echo   启动完成后会自动打开浏览器
echo   关闭本窗口即退出程序
echo ============================================
set PY=%~dp0runtime\python\python.exe
if not exist "%PY%" set PY=python
"%PY%" "%~dp0app\boot.py"
pause
