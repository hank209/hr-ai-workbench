@echo off
cd /d "%~dp0"
echo ============================================
echo  正在构建绿色分发包的运行时（需联网下载 Python 3.11）
echo  此步骤只需执行一次，构建完成后删除本目录即可
echo ============================================
python download_runtime.py
if errorlevel 1 (
    echo.
    echo 构建失败：请检查网络连接后重试。
) else (
    echo.
    echo 构建完成！返回上一级目录，双击 启动工作台.bat 即可使用。
)
pause
