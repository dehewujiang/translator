@echo off
rem 翻译小助手启动脚本：先检查Python，再装依赖，再验零件，最后藏后台运行
title 翻译小助手启动中
cd /d "%~dp0"

echo [1/3] 检查 Python...
where python >nul 2>nul
if errorlevel 1 (
  echo [失败] 没找到 Python，请先安装 Python 3（安装时勾选 Add to PATH），再双击我。
  pause
  exit /b 1
)
python --version

echo.
echo [2/3] 安装依赖（第一次会花 1-2 分钟，不要关这个窗口）...
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo [失败] 依赖装不上，请检查网络后重试，上面有具体报错。
  pause
  exit /b 1
)

echo.
echo [3/3] 检查零件...
python -c "import requests, pyperclip, keyboard, pystray, PIL; print('OK')"
if errorlevel 1 (
  echo [失败] 零件不齐，上面写了缺谁。重双击我一次，或手动跑 pip install -r requirements.txt。
  pause
  exit /b 1
)

echo.
echo 启动翻译小助手（藏后台，右下角小箭头里找“译”字图标）...
start /min "" pythonw "%~dp0app.py"
timeout /t 5 /nobreak >nul